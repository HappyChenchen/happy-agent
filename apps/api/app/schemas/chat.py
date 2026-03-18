"""对话相关的数据模型。"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(
        min_length=1,
        description="会话消息列表，系统会读取最后一条 user 消息。",
    )
    use_tools: bool = Field(default=True, description="是否启用工具流程。")
    max_tool_calls: int = Field(
        default=3,
        ge=0,
        le=10,
        description="单次请求最多执行多少个工具。",
    )


class ToolCallPlan(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResult(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: Any | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    trace_id: str
    answer: str
    llm_used: bool = False
    tool_calls: list[ToolCallResult] = Field(default_factory=list)


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
