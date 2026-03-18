"""计算器工具。

使用受限 AST 解析，只允许数字和基础四则运算，避免执行任意代码。
"""

import ast
import operator
from typing import Callable

_ALLOWED_OPERATORS: dict[type[ast.AST], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARY_OPERATORS: dict[type[ast.AST], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(expression: str) -> float:
    def _eval_node(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            return _ALLOWED_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPERATORS:
            return _ALLOWED_UNARY_OPERATORS[type(node.op)](_eval_node(node.operand))
        raise ValueError("unsupported expression")

    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree)


def tool_calculator(expression: str) -> dict[str, float | str]:
    value = _safe_eval(expression)
    return {"expression": expression, "result": value}

