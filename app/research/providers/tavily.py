from __future__ import annotations

from typing import Any

import httpx

from app.research.base import ResearchProviderError, Source, Topic, clip, now_iso, status_error

_BASE_URL = "https://api.tavily.com"


class TavilyProvider:
    """Tavily search API (fallback after Exa). Free tier: 1,000 credits/month; a basic
    search costs 1 credit, extracting up to 5 URLs costs 1 credit."""

    name = "tavily"

    def __init__(
        self,
        *,
        api_key: str,
        search_depth: str = "basic",
        timeout: float = 15.0,
        max_chars: int = 1500,
    ):
        self._api_key = api_key
        self.search_depth = search_depth
        self.timeout = timeout
        self.max_chars = max_chars

    def __repr__(self) -> str:
        return "TavilyProvider()"

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key:
            raise ResearchProviderError(self.name, "not_configured", "TAVILY_API_KEY is not set")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{_BASE_URL}{path}",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
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
            "search_depth": self.search_depth,
            "topic": topic or "general",
            "max_results": max(1, min(max_results, 20)),
            "include_answer": False,
            "include_raw_content": False,
            "include_published_date": True,
        }
        if recency_days:
            body["time_range"] = _time_range(recency_days)

        data = await self._post("/search", body)
        results = data.get("results")
        if not isinstance(results, list):
            raise ResearchProviderError(self.name, "malformed", "missing results list")

        retrieved_at = now_iso()
        sources = [
            Source(
                title=clip(item.get("title") or item["url"], 200),
                url=item["url"],
                snippet=clip(item.get("content"), self.max_chars),
                source_date=item.get("published_date") or None,
                retrieved_at=retrieved_at,
                provider=self.name,
            )
            for item in results
            if isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"].startswith("http")
        ]
        if not sources:
            raise ResearchProviderError(self.name, "empty", "no results")
        return sources

    async def fetch(self, url: str) -> Source | None:
        data = await self._post("/extract", {"urls": [url], "extract_depth": "basic", "format": "text"})
        for item in data.get("results") or []:
            if isinstance(item, dict) and item.get("raw_content"):
                text = item["raw_content"]
                return Source(
                    title=clip(item.get("title") or url, 200),
                    url=item.get("url") or url,
                    snippet=clip(text, 300),
                    content=clip(text, self.max_chars),
                    source_date=None,
                    retrieved_at=now_iso(),
                    provider=self.name,
                )
        return None


def _time_range(days: int) -> str:
    if days <= 1:
        return "day"
    if days <= 7:
        return "week"
    if days <= 31:
        return "month"
    return "year"
