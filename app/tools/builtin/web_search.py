from __future__ import annotations

import asyncio
import html
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel

_SEARCH_URL = "https://html.duckduckgo.com/html/"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_TITLE_RE = re.compile(r'class="result__a"\s+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>', re.DOTALL)
_SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>(?P<snippet>.*?)</a>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")

_NO_RESULTS_NOTE = (
    "No live search results were found for this query. Do not invent a real-world figure — "
    "tell the founder you could not verify this and clearly label any number you give as an estimate."
)
_FAILED_NOTE = (
    "The web search failed ({error}). Do not invent a real-world figure — tell the founder you "
    "could not verify this and clearly label any number you give as an estimate."
)


class WebSearchInput(BaseModel):
    query: str = Field(
        description="A specific, real-world search query, e.g. 'AWS EC2 t3.micro price India', "
        "'average React developer salary Bangalore 2025', 'Razorpay payment gateway fees India'."
    )
    max_results: int = Field(default=5, ge=1, le=10)


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchOutput(BaseModel):
    query: str
    data_available: bool
    results: list[WebSearchResult]
    note: str


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the live web for real, current information — pricing, costs, salaries, exchange "
        "rates, market statistics, or anything else that must be grounded in reality instead of "
        "guessed. Call this BEFORE financial_analysis or market_research whenever a real number "
        "is needed (e.g. cloud hosting prices, SaaS subscription costs, typical salaries, rent). "
        "Returns real titles, URLs, and text snippets from live search results — read the "
        "snippets and use the actual figures they contain; never fall back to a guessed number "
        "when this tool succeeded."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = WebSearchInput
    output_model = WebSearchOutput

    async def execute(self, payload: WebSearchInput, context: ToolContext) -> dict[str, Any]:
        return await run_search(payload.query, max_results=payload.max_results)


async def run_search(query: str, *, max_results: int = 5) -> dict[str, Any]:
    """Reusable core search — called by the web_search tool itself, and directly by other
    tools (financial_analysis, market_research, competitor_research) so real-world grounding
    doesn't depend on the model remembering to call web_search and thread the results through."""
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_HEADERS, follow_redirects=True) as client:
            response = await client.post(_SEARCH_URL, data={"q": query})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"query": query, "data_available": False, "results": [], "note": _FAILED_NOTE.format(error=str(exc))}

    results = _parse_results(response.text, limit=max_results)
    if not results:
        return {"query": query, "data_available": False, "results": [], "note": _NO_RESULTS_NOTE}

    return {
        "query": query,
        "data_available": True,
        "results": [r.model_dump() for r in results],
        "note": "Live web search results — use these figures, and mention the source when relevant.",
    }


async def search_notes(queries: list[str], *, max_results_per_query: int = 4) -> str:
    """Run several searches and flatten them into a single text block of "title: snippet"
    lines, suitable for pasting into another tool's LLM prompt. Never raises — on total
    failure (e.g. no internet) it returns an empty string so callers can fall back gracefully."""
    try:
        batches = await asyncio.gather(
            *(run_search(q, max_results=max_results_per_query) for q in queries),
            return_exceptions=True,
        )
    except Exception:
        return ""

    lines: list[str] = []
    for batch in batches:
        if isinstance(batch, BaseException) or not batch.get("data_available"):
            continue
        for r in batch["results"]:
            lines.append(f"- {r['title']}: {r['snippet']} (source: {r['url']})")
    return "\n".join(lines)


def _parse_results(page_html: str, *, limit: int) -> list[WebSearchResult]:
    titles = [
        (_clean_url(m.group("href")), _clean_text(m.group("title")))
        for m in _TITLE_RE.finditer(page_html)
    ]
    snippets = [_clean_text(m.group("snippet")) for m in _SNIPPET_RE.finditer(page_html)]

    results: list[WebSearchResult] = []
    for i, (url, title) in enumerate(titles):
        if len(results) >= limit:
            break
        if not url or not title:
            continue
        snippet = snippets[i] if i < len(snippets) else ""
        results.append(WebSearchResult(title=title, url=url, snippet=snippet))
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
