"""工具规划器。

输入用户文本，输出工具调用计划。
当前规则：
1. 支持显式调用语法：`/tool <name> <payload>`。
2. 如果不是显式调用，走关键词 + 正则的启发式规划。
"""

import json
import re
from typing import Any

from app.schemas import ToolCallPlan

_EXPLICIT_TOOL_PATTERN = re.compile(
    r"^\s*(?:/tool|tool:|调用)\s*(?P<name>[A-Za-z_][\w-]*)\s*(?P<payload>.*)\s*$",
    re.IGNORECASE,
)


def _parse_payload(tool_name: str, payload: str) -> dict[str, Any]:
    payload = payload.strip()
    if not payload:
        return {}

    # 支持 JSON 参数：/tool calculator {"expression":"2+2"}
    if payload.startswith("{") and payload.endswith("}"):
        try:
            data = json.loads(payload)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # calculator 默认把剩余文本当作 expression。
    if tool_name == "calculator":
        return {"expression": payload}

    # 兜底：支持 key=value key2=value2
    args: dict[str, Any] = {}
    for token in payload.split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        args[key.strip()] = value.strip()
    return args


def _parse_explicit_tool_call(user_text: str) -> ToolCallPlan | None:
    match = _EXPLICIT_TOOL_PATTERN.match(user_text)
    if not match:
        return None

    name = match.group("name")
    payload = match.group("payload")
    arguments = _parse_payload(tool_name=name, payload=payload)
    return ToolCallPlan(name=name, arguments=arguments)


def _deduplicate_plans(plans: list[ToolCallPlan]) -> list[ToolCallPlan]:
    unique: list[ToolCallPlan] = []
    seen: set[str] = set()

    for plan in plans:
        key = f"{plan.name}:{json.dumps(plan.arguments, sort_keys=True, ensure_ascii=True)}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(plan)

    return unique


def plan_tool_calls_heuristic(user_text: str) -> list[ToolCallPlan]:
    explicit_plan = _parse_explicit_tool_call(user_text)
    if explicit_plan is not None:
        return [explicit_plan]

    plans: list[ToolCallPlan] = []
    lowered = user_text.lower()

    time_keywords = (
        "time",
        "date",
        "\u65f6\u95f4",
        "\u51e0\u70b9",
        "\u65e5\u671f",
    )
    if any(word in lowered for word in time_keywords):
        plans.append(ToolCallPlan(name="get_server_time", arguments={}))

    expr_match = re.search(r"([-+*/().\d\s]{3,})", user_text)
    if expr_match:
        candidate = expr_match.group(1).strip()
        if any(op in candidate for op in ["+", "-", "*", "/", "**"]):
            plans.append(
                ToolCallPlan(name="calculator", arguments={"expression": candidate})
            )

    return _deduplicate_plans(plans)
