from __future__ import annotations

from typing import AsyncIterator

from app.core.errors import ModelTimeoutError, ModelUnavailableError
from app.core.logging import get_logger
from app.models.base import ChatMessage, ModelProvider, ModelResponse, ToolSpec

logger = get_logger(__name__)


class FallbackChatProvider:
    """Tries a primary chat provider first, falling back to a secondary on failure.

    Used for quick chat replies: Gemini first, local Ollama as backup so chat
    keeps working if Gemini keys are missing, rate-limited, or unreachable.
    """

    def __init__(self, *, primary: ModelProvider, fallback: ModelProvider):
        self.primary = primary
        self.fallback = fallback
        self.runtime = f"{primary.runtime}+{fallback.runtime}"
        self.name = primary.name

    async def health(self) -> bool:
        return await self.primary.health() or await self.fallback.health()

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        try:
            return await self.primary.chat(
                messages, tools, temperature=temperature, max_tokens=max_tokens
            )
        except (ModelUnavailableError, ModelTimeoutError) as exc:
            logger.warning("primary_chat_provider_failed", extra={"error": str(exc)})
            return await self.fallback.chat(
                messages, tools, temperature=temperature, max_tokens=max_tokens
            )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        yielded_any = False
        try:
            async for token in self.primary.chat_stream(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                yielded_any = True
                yield token
            return
        except (ModelUnavailableError, ModelTimeoutError) as exc:
            if yielded_any:
                # Primary already streamed partial output; switching providers
                # mid-response would duplicate/garble it, so surface the error.
                raise
            logger.warning("primary_chat_stream_failed", extra={"error": str(exc)})

        async for token in self.fallback.chat_stream(
            messages, temperature=temperature, max_tokens=max_tokens
        ):
            yield token
