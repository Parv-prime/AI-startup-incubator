from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.knowledge.store import KnowledgeStore
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel


class KnowledgeSearchInput(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchOutput(BaseModel):
    items: list[dict]


class KnowledgeSearchTool(BaseTool):
    name = "knowledge_search"
    description = "Retrieve stored reference knowledge documents. Use for facts stored in the knowledge base."
    permission = PermissionLevel.READ_ONLY
    input_model = KnowledgeSearchInput
    output_model = KnowledgeSearchOutput

    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def execute(self, payload: KnowledgeSearchInput, context: ToolContext) -> dict[str, Any]:
        return {"items": await self.store.search(payload.query, payload.limit)}
