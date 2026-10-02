from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    input: str
    user_id: str
    project_id: str
    conversation_id: str | None = None
    confirmed: bool = False


class ToolEvent(BaseModel):
    name: str
    arguments: dict[str, Any]
    status: Literal["ok", "error"]
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float


class AgentResult(BaseModel):
    run_id: str
    project_id: str
    status: Literal["completed", "failed"]
    output: str
    iterations: int
    tool_events: list[ToolEvent] = Field(default_factory=list)
    error_code: str | None = None
    recoverable: bool | None = None
