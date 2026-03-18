"""工具注册中心。

统一维护工具的三个能力：
1. 名字 -> 函数映射。
2. 对外工具描述（给 /tools）。
3. 参数归一化和基础校验。
"""

from typing import Any, Callable

from app.schemas import ToolSpec
from app.tools.calculator import tool_calculator
from app.tools.time_tool import tool_get_server_time

ToolHandler = Callable[..., Any]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "get_server_time": tool_get_server_time,
    "calculator": tool_calculator,
}

TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="get_server_time",
        description="Return current server time.",
        input_schema={"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        name="calculator",
        description="Evaluate a basic math expression.",
        input_schema={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    ),
]

_TOOL_SPECS_BY_NAME: dict[str, ToolSpec] = {spec.name: spec for spec in TOOL_SPECS}


def get_tool_handler(name: str) -> ToolHandler | None:
    return TOOL_HANDLERS.get(name)


def get_tool_spec(name: str) -> ToolSpec | None:
    return _TOOL_SPECS_BY_NAME.get(name)


def get_tool_specs() -> list[ToolSpec]:
    return TOOL_SPECS


def get_tool_names() -> list[str]:
    return list(TOOL_HANDLERS.keys())


def normalize_tool_arguments(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(arguments)

    # 给 calculator 做一些常见参数别名兼容。
    if name == "calculator" and "expression" not in normalized:
        for alias in ("expr", "formula", "input", "text"):
            if alias in normalized and isinstance(normalized[alias], str):
                normalized["expression"] = normalized[alias]
                break
    if name == "calculator":
        for alias in ("expr", "formula", "input", "text"):
            normalized.pop(alias, None)

    return normalized


def _is_type_match(expected_type: str, value: Any) -> bool:
    type_map: dict[str, tuple[type[Any], ...]] = {
        "string": (str,),
        "number": (int, float),
        "integer": (int,),
        "boolean": (bool,),
        "object": (dict,),
        "array": (list,),
    }
    accepted = type_map.get(expected_type)
    if accepted is None:
        return True
    return isinstance(value, accepted)


def validate_tool_arguments(name: str, arguments: dict[str, Any]) -> str | None:
    spec = get_tool_spec(name)
    if spec is None:
        return f"tool not found: {name}"

    schema = spec.input_schema or {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for key in required:
        if key not in arguments:
            return f"missing required argument: {key}"

    for key, value in arguments.items():
        if key not in properties:
            return f"unknown argument: {key}"
        expected_type = properties.get(key, {}).get("type")
        if expected_type and not _is_type_match(expected_type, value):
            return (
                f"invalid argument type for '{key}': "
                f"expected {expected_type}, got {type(value).__name__}"
            )

    return None
