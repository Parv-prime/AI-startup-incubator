from __future__ import annotations

import time
from typing import AsyncIterator, Callable

from app.core.errors import ModelAuthError, ModelRateLimitError, ModelTimeoutError, ModelUnavailableError
from app.core.logging import get_logger
from app.models.base import ChatMessage, ModelProvider, ModelResponse, ToolSpec

logger = get_logger(__name__)

# How long a failing provider is skipped before it is tried first again.
AUTH_COOLDOWN_SECONDS = 3600.0  # bad/revoked key: unlikely to fix itself soon
RATE_LIMIT_COOLDOWN_SECONDS = 60.0  # used when the provider sends no Retry-After
MAX_RATE_LIMIT_COOLDOWN_SECONDS = 3600.0
TRANSIENT_COOLDOWN_SECONDS = 30.0  # timeouts, network errors, 5xx


class ProviderPool:
    """Ordered failover across several cloud LLM providers (e.g. 3 Groq keys, then 3 Gemini keys).

    Each call tries providers in configured order, skipping ones that recently
    failed (rate-limited, bad key, outage) until their cooldown expires. If every
    provider is cooling down they are still tried, soonest-available first, so a
    request is never refused without an attempt.
    """

    runtime = "cloud"

    def __init__(self, providers: list[ModelProvider], *, clock: Callable[[], float] = time.monotonic):
        if not providers:
            raise ValueError("ProviderPool needs at least one provider")
        self.providers = providers
        self.name = providers[0].name
        self._clock = clock
        self._cooldown_until = [0.0] * len(providers)

    def __repr__(self) -> str:
        return f"ProviderPool({[_label(p) for p in self.providers]!r})"

    def _order(self) -> list[int]:
        now = self._clock()
        indexes = range(len(self.providers))
        ready = [i for i in indexes if self._cooldown_until[i] <= now]
        cooling = sorted((i for i in indexes if self._cooldown_until[i] > now), key=lambda i: self._cooldown_until[i])
        return ready + cooling

    def _record_failure(self, index: int, exc: Exception) -> None:
        cooldown = _cooldown_for(exc)
        self._cooldown_until[index] = self._clock() + cooldown
        logger.warning(
            "llm_pool_provider_failed",
            extra={
                "provider": _label(self.providers[index]),
                "error": getattr(exc, "code", type(exc).__name__),
                "cooldown_seconds": cooldown,
            },
        )

    def _record_success(self, index: int) -> None:
        self._cooldown_until[index] = 0.0

    async def health(self) -> bool:
        for index in self._order():
            if await self.providers[index].health():
                return True
        return False

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        last_error: Exception | None = None
        for index in self._order():
            try:
                response = await self.providers[index].chat(
                    messages, tools, temperature=temperature, max_tokens=max_tokens
                )
            except (ModelUnavailableError, ModelTimeoutError) as exc:
                self._record_failure(index, exc)
                last_error = exc
                continue
            self._record_success(index)
            return response
        assert last_error is not None
        raise last_error

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        last_error: Exception | None = None
        for index in self._order():
            yielded_any = False
            try:
                async for token in self.providers[index].chat_stream(
                    messages, temperature=temperature, max_tokens=max_tokens
                ):
                    yielded_any = True
                    yield token
            except (ModelUnavailableError, ModelTimeoutError) as exc:
                self._record_failure(index, exc)
                if yielded_any:
                    # Partial output already reached the user; switching providers
                    # mid-response would duplicate/garble it, so surface the error.
                    raise
                last_error = exc
                continue
            self._record_success(index)
            return
        assert last_error is not None
        raise last_error


def _label(provider: ModelProvider) -> str:
    return getattr(provider, "label", None) or provider.name


def _cooldown_for(exc: Exception) -> float:
    if isinstance(exc, ModelAuthError):
        return AUTH_COOLDOWN_SECONDS
    details = getattr(exc, "details", None) or {}
    if isinstance(exc, ModelRateLimitError):
        retry_after = details.get("retry_after")
        if isinstance(retry_after, (int, float)) and retry_after > 0:
            return min(float(retry_after), MAX_RATE_LIMIT_COOLDOWN_SECONDS)
        return RATE_LIMIT_COOLDOWN_SECONDS
    status = details.get("status")
    if isinstance(status, int) and 400 <= status < 500:
        # Rejected this particular request (bad payload/model); the key itself is fine.
        return 0.0
    return TRANSIENT_COOLDOWN_SECONDS
