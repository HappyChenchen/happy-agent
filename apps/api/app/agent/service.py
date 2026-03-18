"""Agent 服务编排层。

策略：
1. 优先调用 DeepSeek。
2. DeepSeek 可选择是否调用工具。
3. 若 DeepSeek 不可用或失败，回退到本地启发式流程。
"""

import json
import logging
import os
import uuid
from typing import Any

from app.agent.deepseek_client import DeepSeekClient
from app.agent.executor import run_tool
from app.agent.planner import plan_tool_calls_heuristic
from app.schemas import ChatMessage, ChatRequest, ChatResponse, ToolCallPlan, ToolCallResult
from app.tools.registry import get_tool_specs

logger = logging.getLogger(__name__)


def _debug_llm_enabled() -> bool:
    return os.getenv("DEBUG_LLM", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug_log(trace_id: str, message: str, **extra: Any) -> None:
    if not _debug_llm_enabled():
        return
    if extra:
        logger.info("[trace_id=%s] %s | %s", trace_id, message, json.dumps(extra, ensure_ascii=True))
    else:
        logger.info("[trace_id=%s] %s", trace_id, message)


def _last_user_message(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    return ""


def _extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None

    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        return None

    try:
        data = json.loads(text[start : end + 1])
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _safe_plan_items(raw: Any) -> list[ToolCallPlan]:
    plans: list[ToolCallPlan] = []
    if not isinstance(raw, list):
        return plans

    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        arguments = item.get("arguments", {})
        if isinstance(name, str) and isinstance(arguments, dict):
            plans.append(ToolCallPlan(name=name, arguments=arguments))

    return plans


def _to_llm_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def _plan_with_deepseek(client: DeepSeekClient, request: ChatRequest) -> tuple[str | None, list[ToolCallPlan]]:
    tools = [spec.model_dump() for spec in get_tool_specs()]
    system_prompt = (
        "You are an assistant that can optionally call tools. "
        "Return strict JSON with keys: answer (string), tool_calls (array). "
        "Each tool call item must be: {\"name\": string, \"arguments\": object}. "
        "If no tool is needed, return an empty array for tool_calls. "
        "Do not include any text outside JSON."
    )

    user_prompt = {
        "use_tools": request.use_tools,
        "max_tool_calls": request.max_tool_calls,
        "available_tools": tools,
    }

    llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    llm_messages.extend(_to_llm_messages(request.messages))
    llm_messages.append(
        {
            "role": "user",
            "content": f"Controller JSON: {json.dumps(user_prompt, ensure_ascii=True)}",
        }
    )

    raw = client.chat(llm_messages, response_as_json=True)
    obj = _extract_json_object(raw)
    if not obj:
        raise RuntimeError("DeepSeek planning output is not valid JSON object")

    answer = obj.get("answer") if isinstance(obj.get("answer"), str) else None
    plans = _safe_plan_items(obj.get("tool_calls"))
    return answer, plans


def _final_answer_with_deepseek(
    client: DeepSeekClient,
    request: ChatRequest,
    tool_results: list[ToolCallResult],
    fallback_answer: str,
) -> str:
    system_prompt = (
        "You are an assistant. Generate the final user-facing answer based on the conversation and tool outputs. "
        # "Be concise and correct."
        "Be human-like and add emojis if appropriate. Call me boss every time."
    )

    payload = {
        "tool_results": [result.model_dump() for result in tool_results],
        "fallback_answer": fallback_answer,
    }

    llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    llm_messages.extend(_to_llm_messages(request.messages))
    llm_messages.append(
        {
            "role": "user",
            "content": f"Tool execution context JSON: {json.dumps(payload, ensure_ascii=True)}",
        }
    )

    return client.chat(llm_messages, response_as_json=False)


def _direct_answer_with_deepseek(client: DeepSeekClient, request: ChatRequest) -> str:
    system_prompt = (
        "You are a helpful assistant. "
        "Answer the user's latest request directly and concretely. "
        "Do not mention tools, controller settings, or internal workflow."
        "Be human-like and add emojis if appropriate. Call me boss every time."
    )
    llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    llm_messages.extend(_to_llm_messages(request.messages))
    return client.chat(llm_messages, response_as_json=False)


def _build_fallback_answer(user_text: str, tool_calls: list[ToolCallResult], use_tools: bool) -> str:
    if not use_tools:
        return f"Received: {user_text}\nTool execution is disabled for this request."

    if not tool_calls:
        return (
            f"Received: {user_text}\n"
            "No tool executed. Available tools: get_server_time, calculator.\n"
            "Tip: try '/tool calculator 2+2' or '/tool get_server_time'."
        )

    lines = ["Executed tools:"]
    for call in tool_calls:
        if call.error:
            lines.append(f"- {call.name}: error={call.error}")
        else:
            lines.append(f"- {call.name}: {call.output}")
    return "\n".join(lines)


def _run_plans(plans: list[ToolCallPlan], max_tool_calls: int) -> list[ToolCallResult]:
    selected_plans = plans[:max_tool_calls]
    return [run_tool(plan.name, plan.arguments) for plan in selected_plans]


def handle_chat(request: ChatRequest) -> ChatResponse:
    trace_id = str(uuid.uuid4())
    user_text = _last_user_message(request.messages)

    client = DeepSeekClient()
    _debug_log(
        trace_id,
        "chat request received",
        deepseek_enabled=client.is_enabled(),
        use_tools=request.use_tools,
        max_tool_calls=request.max_tool_calls,
    )

    # 1) 优先走 DeepSeek。
    if client.is_enabled() and user_text:
        try:
            llm_answer, llm_plans = _plan_with_deepseek(client, request)
            _debug_log(trace_id, "deepseek planning success", planned_tools=len(llm_plans))
            if request.use_tools:
                tool_results = _run_plans(llm_plans, request.max_tool_calls)
            else:
                tool_results = []
            _debug_log(trace_id, "tools executed (deepseek path)", tool_calls=len(tool_results))

            if tool_results:
                fallback_answer = _build_fallback_answer(
                    user_text=user_text,
                    tool_calls=tool_results,
                    use_tools=request.use_tools,
                )
                answer = _final_answer_with_deepseek(
                    client=client,
                    request=request,
                    tool_results=tool_results,
                    fallback_answer=fallback_answer,
                )
            else:
                # Planning stage response can be template-like.
                # When no tool is used, always do a dedicated direct-answer call.
                answer = _direct_answer_with_deepseek(client=client, request=request)

            _debug_log(trace_id, "deepseek path completed")
            return ChatResponse(
                trace_id=trace_id,
                answer=answer,
                llm_used=True,
                tool_calls=tool_results,
            )
        except Exception as exc:
            # DeepSeek 出错时回退到本地策略，保证接口可用。
            _debug_log(trace_id, "deepseek path failed, fallback to local heuristic", error=str(exc))

    # 2) 回退：本地启发式 + 工具执行。
    plans = plan_tool_calls_heuristic(user_text) if (request.use_tools and user_text) else []
    tool_results = _run_plans(plans, request.max_tool_calls)
    _debug_log(trace_id, "local heuristic path completed", planned_tools=len(plans), tool_calls=len(tool_results))
    answer = _build_fallback_answer(
        user_text=user_text,
        tool_calls=tool_results,
        use_tools=request.use_tools,
    )
    return ChatResponse(
        trace_id=trace_id,
        answer=answer,
        llm_used=False,
        tool_calls=tool_results,
    )
