from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: str = "New Conversation"


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1)


class ConversationResponse(BaseModel):
    id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class ToolActivity(BaseModel):
    tool_name: str
    status: Literal["completed", "failed"]
    message: str
    duration_ms: int | None = None


class AnalysisResponse(BaseModel):
    market_research: dict | None = None
    competitor_research: dict | None = None
    financial_analysis: dict | None = None


class Recommendation(BaseModel):
    title: str
    description: str
    priority: Literal["High", "Medium", "Low"]
    category: str


class Source(BaseModel):
    title: str
    url: str | None = None
    source_type: str


class SendMessageResponse(BaseModel):
    success: bool
    response: str
    conversation_id: str
    project_id: str
    path: Literal["fast", "agent"]
    tool_activity: list[ToolActivity] = Field(default_factory=list)
    analysis: AnalysisResponse | None = None
    viability: dict | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
