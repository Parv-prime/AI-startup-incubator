from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.research.base import ResearchProviderError, Source, Topic, clip, now_iso, status_error

_BASE_URL = "https://api.exa.ai"


class ExaProvider:
    """Exa search API (primary provider). Free tier: a monthly credit that
    resets on the 1st; good at finding company/product pages."""

    name = "exa"

    def __init__(self, *, api_key: str, timeout: float = 15.0, max_chars: int = 1500):
        self._api_key = api_key
        self.timeout = timeout
        self.max_chars = max_chars

    def __repr__(self) -> str:
        return "ExaProvider()"

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key:
            raise ResearchProviderError(self.name, "not_configured", "EXA_API_KEY is not set")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{_BASE_URL}{path}", headers={"x-api-key": self._api_key}, json=body
                )
        except httpx.TimeoutException as exc:
            raise ResearchProviderError(self.name, "timeout", "request timed out") from exc
        except httpx.HTTPError as exc:
            raise ResearchProviderError(self.name, "network", type(exc).__name__) from exc
        if response.status_code >= 400:
            raise status_error(self.name, response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise ResearchProviderError(self.name, "malformed", "non-JSON response") from exc
        if not isinstance(data, dict):
            raise ResearchProviderError(self.name, "malformed", "unexpected response shape")
        return data

    async def search(
        self,
        query: str,
        max_results: int = 5,
        recency_days: int | None = None,
        *,
        topic: Topic | None = None,
    ) -> list[Source]:
        body: dict[str, Any] = {
            "query": query,
            "numResults": max(1, min(max_results, 25)),
            "type": "auto",
            "contents": {"text": {"maxCharacters": self.max_chars}},
        }
        if topic == "news":
            body["category"] = "news"
        if recency_days:
            start = datetime.now(timezone.utc) - timedelta(days=recency_days)
            body["startPublishedDate"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")

        data = await self._post("/search", body)
        results = data.get("results")
        if not isinstance(results, list):
            raise ResearchProviderError(self.name, "malformed", "missing results list")

        retrieved_at = now_iso()
        sources = [_to_source(item, retrieved_at, self.max_chars) for item in results if _usable(item)]
        if not sources:
            raise ResearchProviderError(self.name, "empty", "no results")
        return sources

    async def fetch(self, url: str) -> Source | None:
        data = await self._post("/contents", {"urls": [url], "text": {"maxCharacters": self.max_chars}})
        for item in data.get("results") or []:
            if _usable(item) and item.get("text"):
                return _to_source(item, now_iso(), self.max_chars)
        return None


def _usable(item: Any) -> bool:
    return isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"].startswith("http")


def _to_source(item: dict[str, Any], retrieved_at: str, max_chars: int) -> Source:
    text = item.get("text") or ""
    highlights = item.get("highlights")
    snippet = " … ".join(h for h in highlights if isinstance(h, str)) if isinstance(highlights, list) else ""
    return Source(
        title=clip(item.get("title") or item["url"], 200),
        url=item["url"],
        snippet=clip(snippet or text, 500),
        content=clip(text, max_chars) or None,
        source_date=item.get("publishedDate") or None,
        retrieved_at=retrieved_at,
        provider="exa",
    )
