from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.memory.store import MemoryStore
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel


class MemoryWriteInput(BaseModel):
    content: str = Field(description="The fact, decision, assumption, open question, or risk to remember.")
    category: Literal["fact", "decision", "assumption", "open_question", "risk", "note"] = Field(
        default="fact",
        description=(
            "fact = confirmed information the founder stated. decision = a choice the founder "
            "explicitly confirmed — never store your own suggestion as a decision unless the "
            "user agreed to it. assumption = believed true but not yet validated. "
            "open_question = still unresolved. risk = a known risk to track."
        ),
    )


class MemoryWriteOutput(BaseModel):
    id: str
    project_id: str
    category: str
    content: str


class MemorySearchInput(BaseModel):
    query: str = Field(description="Text to search in this project's memory.")
    limit: int = Field(default=5, ge=1, le=20)


class MemorySearchOutput(BaseModel):
    items: list[dict]


class MemoryWriteTool(BaseTool):
    name = "memory_write"
    description = (
        "Store a durable fact, confirmed decision, assumption, open question, or risk in this "
        "project's isolated long-term memory. Only categorize something as a 'decision' if the "
        "founder actually confirmed it — your own recommendation is not a decision until they agree."
    )
    permission = PermissionLevel.WRITE
    input_model = MemoryWriteInput
    output_model = MemoryWriteOutput

    def __init__(self, store: MemoryStore):
        self.store = store

    async def execute(self, payload: MemoryWriteInput, context: ToolContext) -> dict[str, Any]:
        return await self.store.add(context.project_id, payload.content, payload.category)


class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = "Search this project's isolated long-term memory. Never returns another project's data."
    permission = PermissionLevel.READ_ONLY
    input_model = MemorySearchInput
    output_model = MemorySearchOutput

    def __init__(self, store: MemoryStore):
        self.store = store

    async def execute(self, payload: MemorySearchInput, context: ToolContext) -> dict[str, Any]:
        items = await self.store.search(context.project_id, payload.query, payload.limit)
        return {"items": items}
