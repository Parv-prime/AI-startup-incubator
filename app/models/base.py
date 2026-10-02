from __future__ import annotations

from typing import Any, AsyncIterator, Protocol

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ModelUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ModelResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: ModelUsage | None = None
    finish_reason: str | None = None


class ModelProvider(Protocol):
    name: str
    runtime: str

    async def health(self) -> bool: ...

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse: ...

    def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield response text deltas as they are generated (no tool-calling)."""
        ...
