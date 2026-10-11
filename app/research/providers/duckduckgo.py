"""DuckDuckGo HTML results page — last-resort, no-key fallback.

There is no official DuckDuckGo search API; this scrapes html.duckduckgo.com.
It usually works from a home connection but is frequently rate-limited or
blocked from cloud/datacenter IPs, so it is never the primary provider.
"""

from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.research.base import ResearchProviderError, Source, Topic, clip, now_iso, status_error
from app.research.reader import USER_AGENT, DirectPageReader

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_TITLE_RE = re.compile(r'class="result__a"\s+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>', re.DOTALL)
_SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>(?P<snippet>.*?)</a>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


class DuckDuckGoProvider:
    name = "duckduckgo"

    def __init__(self, *, timeout: float = 10.0, max_chars: int = 1500):
        self.timeout = timeout
        self.max_chars = max_chars
        self._reader = DirectPageReader(timeout=timeout, max_chars=max_chars)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        recency_days: int | None = None,
        *,
        topic: Topic | None = None,
    ) -> list[Source]:
        form = {"q": query}
        if recency_days:
            form["df"] = "d" if recency_days <= 1 else "w" if recency_days <= 7 else "m" if recency_days <= 31 else "y"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
            ) as client:
                response = await client.post(_SEARCH_URL, data=form)
        except httpx.TimeoutException as exc:
            raise ResearchProviderError(self.name, "timeout", "request timed out") from exc
        except httpx.HTTPError as exc:
            raise ResearchProviderError(self.name, "network", type(exc).__name__) from exc

        # DuckDuckGo signals bot-blocking with HTTP 202 and an "anomaly" challenge page.
        if response.status_code == 202 or "anomaly-modal" in response.text:
            raise ResearchProviderError(self.name, "rate_limit", "blocked or rate-limited")
        if response.status_code >= 400:
            raise status_error(self.name, response.status_code)

        sources = parse_results(response.text, limit=max_results, max_chars=self.max_chars)
        if not sources:
            raise ResearchProviderError(self.name, "empty", "no results")
        return sources

    async def fetch(self, url: str) -> Source | None:
        return await self._reader.fetch(url)


def parse_results(page_html: str, *, limit: int, max_chars: int = 1500) -> list[Source]:
    titles = [
        (_clean_url(m.group("href")), _clean_text(m.group("title")))
        for m in _TITLE_RE.finditer(page_html)
    ]
    snippets = [_clean_text(m.group("snippet")) for m in _SNIPPET_RE.finditer(page_html)]

    retrieved_at = now_iso()
    results: list[Source] = []
    for i, (url, title) in enumerate(titles):
        if len(results) >= limit:
            break
        if not url or not title or not url.startswith("http"):
            continue
        # Skip DuckDuckGo's own ad redirects.
        if "duckduckgo.com/y.js" in url:
            continue
        snippet = snippets[i] if i < len(snippets) else ""
        results.append(
            Source(
                title=clip(title, 200),
                url=url,
                snippet=clip(snippet, max_chars),
                source_date=None,  # the HTML results page does not expose dates
                retrieved_at=retrieved_at,
                provider="duckduckgo",
            )
        )
    return results


def _clean_text(value: str) -> str:
    return html.unescape(_TAG_RE.sub("", value)).strip()


def _clean_url(href: str) -> str:
    href = html.unescape(href)
    if "duckduckgo.com/l/" in href:
        parsed = urlparse(href if href.startswith("http") else f"https:{href}")
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return unquote(target[0])
    return href
