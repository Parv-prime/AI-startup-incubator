"""Provider-independent research types.

Every search backend (Tavily, Exa, DuckDuckGo, ...) returns the same `Source`
shape, so research tools never need to know which engine answered.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel

Topic = Literal["general", "news"]

UNAVAILABLE_MESSAGE = "Live research is currently unavailable."


class Source(BaseModel):
    title: str
    url: str
    snippet: str = ""
    # Longer extracted page text, when the page itself was fetched/read.
    content: str | None = None
    # Publication date as reported by the provider/page. Never guessed: None when unknown.
    source_date: str | None = None
    retrieved_at: str
    provider: str

    @property
    def domain(self) -> str:
        return domain_of(self.url)

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.snippet}\n{self.content or ''}"


class ResearchProviderError(Exception):
    """A single provider failed. `kind` drives logging and fallback decisions."""

    def __init__(self, provider: str, kind: str, message: str):
        super().__init__(f"{provider}: {kind}: {message}")
        self.provider = provider
        self.kind = kind  # not_configured | auth | rate_limit | timeout | network | http | malformed | empty
        self.message = message


class ResearchUnavailableError(Exception):
    """Every configured provider failed — there is no live research to offer."""

    def __init__(self, failures: list[ResearchProviderError] | None = None):
        super().__init__(UNAVAILABLE_MESSAGE)
        self.failures = failures or []


class ResearchProvider(Protocol):
    name: str

    async def search(
        self,
        query: str,
        max_results: int = 5,
        recency_days: int | None = None,
        *,
        topic: Topic | None = None,
    ) -> list[Source]: ...

    async def fetch(self, url: str) -> Source | None: ...


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def domain_of(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def clip(text: str | None, limit: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def status_error(provider: str, status: int) -> ResearchProviderError:
    if status in (401, 403):
        return ResearchProviderError(provider, "auth", f"rejected credentials (HTTP {status})")
    if status in (402, 429, 432, 433):
        # 402/432/433 are how some providers signal an exhausted free quota.
        return ResearchProviderError(provider, "rate_limit", f"rate limit or quota reached (HTTP {status})")
    return ResearchProviderError(provider, "http", f"HTTP {status}")
