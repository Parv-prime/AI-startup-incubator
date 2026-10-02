from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import ToolExecutionError
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel

KNOWLEDGE_ROOT = Path.cwd() / "data" / "knowledge"


class FileReadInput(BaseModel):
    relative_path: str = Field(description="Path relative to data/knowledge/. Path traversal is rejected.")


class FileReadOutput(BaseModel):
    path: str
    content: str


class FileReaderTool(BaseTool):
    name = "file_reader"
    description = "Read a UTF-8 text file from the sandboxed data/knowledge directory only."
    permission = PermissionLevel.READ_ONLY
    input_model = FileReadInput
    output_model = FileReadOutput

    async def execute(self, payload: FileReadInput, context: ToolContext) -> dict[str, Any]:
        KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
        candidate = (KNOWLEDGE_ROOT / payload.relative_path).resolve()
        try:
            candidate.relative_to(KNOWLEDGE_ROOT.resolve())
        except ValueError as exc:
            raise ToolExecutionError("Path is outside the knowledge sandbox.") from exc
        if not candidate.is_file():
            raise ToolExecutionError("File not found in the knowledge sandbox.")
        return {"path": str(candidate.relative_to(Path.cwd())), "content": candidate.read_text(encoding="utf-8")}
