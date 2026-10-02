from __future__ import annotations

import ast
import operator
from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import ToolExecutionError
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class CalculatorInput(BaseModel):
    expression: str = Field(description="Arithmetic expression using +, -, *, /, //, %, ** and parentheses.")


class CalculatorOutput(BaseModel):
    expression: str
    result: float


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Evaluate a numeric arithmetic expression. Use this for any multiplication, "
        "division, addition, subtraction, or exponentiation instead of guessing."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = CalculatorInput
    output_model = CalculatorOutput

    async def execute(self, payload: CalculatorInput, context: ToolContext) -> dict[str, Any]:
        expression = _normalize(payload.expression)
        try:
            result = _safe_eval(expression)
        except Exception as exc:
            raise ToolExecutionError(
                "Could not evaluate the arithmetic expression.",
                details={"expression": payload.expression, "error": str(exc)},
            ) from exc
        if isinstance(result, bool) or not isinstance(result, (int, float)):
            raise ToolExecutionError("Expression did not produce a number.")
        return {"expression": expression, "result": float(result)}


def _normalize(expression: str) -> str:
    return (
        expression.replace("×", "*")
        .replace("x", "*")
        .replace("X", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .strip()
    )


def _safe_eval(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    raise ValueError("Unsupported expression")
