"""HTTP 路由层。

本文件只做三件事：
1. 接收请求。
2. 调用服务层。
3. 返回统一响应。
"""

from fastapi import APIRouter

from app.agent.service import handle_chat
from app.schemas import ChatRequest, ChatResponse, ToolSpec
from app.tools.registry import get_tool_specs

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/tools")
def list_tools() -> dict[str, list[ToolSpec]]:
    return {"tools": get_tool_specs()}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return handle_chat(request)

