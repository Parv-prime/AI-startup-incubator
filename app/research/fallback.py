from __future__ import annotations

from app.core.logging import get_logger
from app.research.base import (
    ResearchProvider,
    ResearchProviderError,
    ResearchUnavailableError,
    Source,
    Topic,
)

logger = get_logger(__name__)


class FallbackResearchProvider:
    """Tries each search provider in order (e.g. Tavily → Exa → DuckDuckGo).

    A provider "fails" on timeout, bad/missing credentials, rate limit, server
    error, malformed or empty response — then the next one is tried. If every
    provider *errored*, ResearchUnavailableError is raised. If at least one
    provider answered but found nothing, an empty list is returned (research
    worked; there was simply no evidence).

    `fetch` reads a known URL using the page readers first (Jina, direct HTTP),
    then the providers' own fetch/extract endpoints, and returns None if no
    reader could get the page.
    """

    name = "fallback"

    def __init__(self, providers: list[ResearchProvider], readers: list | None = None):
        self.providers = providers
        self.readers = readers or []

    @property
    def provider_names(self) -> list[str]:
        return [p.name for p in self.providers]

    async def search(
        self,
        query: str,
        max_results: int = 5,
        recency_days: int | None = None,
        *,
        topic: Topic | None = None,
    ) -> list[Source]:
        failures: list[ResearchProviderError] = []
        answered_empty = False
        for provider in self.providers:
            try:
                results = await provider.search(query, max_results, recency_days, topic=topic)
            except ResearchProviderError as exc:
                _log_failure(provider.name, exc.kind, exc.message)
                if exc.kind == "empty":
                    answered_empty = True
                failures.append(exc)
                continue
            except Exception as exc:  # a provider bug must not crash the agent
                _log_failure(provider.name, "unexpected", type(exc).__name__)
                failures.append(ResearchProviderError(provider.name, "unexpected", type(exc).__name__))
                continue
            if results:
                if failures:
                    logger.info(
                        "research_fallback_used",
                        extra={"provider": provider.name, "failed": [f.provider for f in failures]},
                    )
                return results[:max_results]
            answered_empty = True

        if answered_empty:
            return []
        raise ResearchUnavailableError(failures)

    async def fetch(self, url: str) -> Source | None:
        for reader in [*self.readers, *self.providers]:
            try:
                page = await reader.fetch(url)
            except ResearchProviderError as exc:
                _log_failure(reader.name, exc.kind, exc.message, action="fetch")
                continue
            except Exception as exc:
                _log_failure(reader.name, "unexpected", type(exc).__name__, action="fetch")
                continue
            if page is not None:
                return page
        return None


def _log_failure(provider: str, kind: str, message: str, *, action: str = "search") -> None:
    # Messages are built by our providers and never contain API keys.
    logger.warning(
        "research_provider_failed",
        extra={"provider": provider, "action": action, "kind": kind, "detail": message},
    )
