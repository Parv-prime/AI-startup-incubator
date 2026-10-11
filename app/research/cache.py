from __future__ import annotations

import time
from collections import OrderedDict

from app.research.base import ResearchProvider, Source, Topic


class CachedResearchProvider:
    """Short-lived in-memory cache in front of any ResearchProvider.

    Cached `Source`s keep their original `retrieved_at`, so callers can always
    tell (and show) how old the evidence is — cached results are never
    presented as freshly retrieved. Only non-empty results are cached. The
    cache is per-process and is lost on restart, which is fine for its purpose
    (saving free-tier API credits on repeated questions).
    """

    def __init__(self, inner: ResearchProvider, *, ttl_seconds: int, max_entries: int = 256):
        self.inner = inner
        self.name = inner.name
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[tuple, tuple[float, list[Source]]] = OrderedDict()

    def __getattr__(self, item):  # expose e.g. provider_names of the wrapped provider
        if item == "inner":
            raise AttributeError(item)
        return getattr(self.inner, item)

    def _get(self, key: tuple) -> list[Source] | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > self.ttl_seconds:
            self._entries.pop(key, None)
            return None
        self._entries.move_to_end(key)
        return [source.model_copy() for source in value]

    def _put(self, key: tuple, value: list[Source]) -> None:
        self._entries[key] = (time.monotonic(), [source.model_copy() for source in value])
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        recency_days: int | None = None,
        *,
        topic: Topic | None = None,
    ) -> list[Source]:
        key = ("search", " ".join(query.lower().split()), max_results, recency_days, topic)
        cached = self._get(key)
        if cached is not None:
            return cached
        results = await self.inner.search(query, max_results, recency_days, topic=topic)
        if results:
            self._put(key, results)
        return results

    async def fetch(self, url: str) -> Source | None:
        key = ("fetch", url)
        cached = self._get(key)
        if cached is not None:
            return cached[0]
        page = await self.inner.fetch(url)
        if page is not None:
            self._put(key, [page])
        return page

    def clear(self) -> None:
        self._entries.clear()
