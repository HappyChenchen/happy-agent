"""工具执行器。

职责：
1. 找到目标工具。
2. 归一化参数。
3. 做基础参数校验。
4. 执行并返回统一结构。
"""

from typing import Any

from app.schemas import ToolCallResult
from app.tools.registry import (
    get_tool_handler,
    get_tool_names,
    normalize_tool_arguments,
    validate_tool_arguments,
)


def run_tool(name: str, arguments: dict[str, Any]) -> ToolCallResult:
    handler = get_tool_handler(name)
    if handler is None:
        available = ", ".join(get_tool_names())
        return ToolCallResult(
            name=name,
            arguments=arguments,
            error=f"tool not found: {name}. available: {available}",
        )

    normalized_args = normalize_tool_arguments(name=name, arguments=arguments)
    validation_error = validate_tool_arguments(name=name, arguments=normalized_args)
    if validation_error:
        return ToolCallResult(
            name=name,
            arguments=normalized_args,
            error=validation_error,
        )

    try:
        output = handler(**normalized_args)
        return ToolCallResult(name=name, arguments=normalized_args, output=output)
    except Exception as exc:  # noqa: BLE001
        return ToolCallResult(name=name, arguments=normalized_args, error=str(exc))
