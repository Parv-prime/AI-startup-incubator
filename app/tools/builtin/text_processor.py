from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel


class TextProcessInput(BaseModel):
    text: str
    operation: Literal["word_count", "uppercase", "lowercase", "trim"]


class TextProcessOutput(BaseModel):
    operation: str
    result: str | int


class TextProcessorTool(BaseTool):
    name = "text_processor"
    description = "Deterministic text operations: word_count, uppercase, lowercase, trim."
    permission = PermissionLevel.READ_ONLY
    input_model = TextProcessInput
    output_model = TextProcessOutput

    async def execute(self, payload: TextProcessInput, context: ToolContext) -> dict[str, Any]:
        text = payload.text
        if payload.operation == "word_count":
            return {"operation": payload.operation, "result": len(text.split())}
        if payload.operation == "uppercase":
            return {"operation": payload.operation, "result": text.upper()}
        if payload.operation == "lowercase":
            return {"operation": payload.operation, "result": text.lower()}
        return {"operation": payload.operation, "result": text.strip()}
