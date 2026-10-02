from typing import Literal

from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    category: Literal["fact", "decision", "assumption", "open_question", "risk", "note"] = "fact"


class MemoryListResponse(BaseModel):
    project_id: str
    items: list[dict]


class KnowledgeCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
