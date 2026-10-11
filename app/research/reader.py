"""Page readers: turn a URL we already have into readable text.

Used for fetching a specific page (official site, pricing page, article) after
search. JinaReader is tried first (handles JS-heavy pages, works without a key
at a low rate limit); `DirectPageReader` is a plain HTTP fallback that needs no
third-party service at all.
"""

from __future__ import annotations

import html
import ipaddress
import re
from urllib.parse import quote, urlparse

import httpx

from app.research.base import ResearchProviderError, Source, clip, now_iso, status_error

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_MAX_DOWNLOAD_BYTES = 1_500_000

_SCRIPT_RE = re.compile(r"<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_DATE_META_RE = re.compile(
    r'<meta[^>]+(?:property|name|itemprop)=["\'](?:article:published_time|datePublished|'
    r'pubdate|publish-date|og:published_time|date)["\'][^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def is_safe_public_url(url: str) -> bool:
    """Only fetch public http(s) URLs — never localhost or private network addresses."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return "." in host  # a normal DNS name


async def _guard_redirect(request: httpx.Request) -> None:
    if not is_safe_public_url(str(request.url)):
        raise httpx.RequestError("Blocked non-public URL", request=request)


class JinaReader:
    name = "jina"

    def __init__(self, *, api_key: str = "", timeout: float = 15.0, max_chars: int = 1500):
        self._api_key = api_key
        self.timeout = timeout
        self.max_chars = max_chars

    async def fetch(self, url: str) -> Source | None:
        if not is_safe_public_url(url):
            return None
        headers = {"Accept": "application/json", "X-Return-Format": "text"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"https://r.jina.ai/{quote(url, safe=':/?&=%#')}", headers=headers)
        except httpx.TimeoutException as exc:
            raise ResearchProviderError(self.name, "timeout", "page read timed out") from exc
        except httpx.HTTPError as exc:
            raise ResearchProviderError(self.name, "network", type(exc).__name__) from exc
        if response.status_code >= 400:
            raise status_error(self.name, response.status_code)
        try:
            data = (response.json() or {}).get("data") or {}
        except ValueError as exc:
            raise ResearchProviderError(self.name, "malformed", "non-JSON response") from exc
        content = data.get("content") or data.get("text") or ""
        if not content.strip():
            return None
        return Source(
            title=clip(data.get("title") or url, 200),
            url=data.get("url") or url,
            snippet=clip(content, 300),
            content=clip(content, self.max_chars),
            source_date=data.get("publishedTime") or None,
            retrieved_at=now_iso(),
            provider=self.name,
        )


class DirectPageReader:
    """No-key fallback: download the HTML ourselves and strip it to text."""

    name = "direct"

    def __init__(self, *, timeout: float = 15.0, max_chars: int = 1500):
        self.timeout = timeout
        self.max_chars = max_chars

    async def fetch(self, url: str) -> Source | None:
        if not is_safe_public_url(url):
            return None
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                event_hooks={"request": [_guard_redirect]},
            ) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code >= 400:
                        raise status_error(self.name, response.status_code)
                    content_type = response.headers.get("content-type", "")
                    if "html" not in content_type and "text" not in content_type:
                        return None
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) >= _MAX_DOWNLOAD_BYTES:
                            break
                    final_url = str(response.url)
                    encoding = response.encoding or "utf-8"
        except httpx.TimeoutException as exc:
            raise ResearchProviderError(self.name, "timeout", "page fetch timed out") from exc
        except httpx.HTTPError as exc:
            raise ResearchProviderError(self.name, "network", type(exc).__name__) from exc

        page = body.decode(encoding, errors="replace")
        text = html_to_text(page)
        if not text:
            return None
        title_match = _TITLE_RE.search(page)
        date_match = _DATE_META_RE.search(page)
        return Source(
            title=clip(html.unescape(title_match.group(1)) if title_match else final_url, 200),
            url=final_url,
            snippet=clip(text, 300),
            content=clip(text, self.max_chars),
            source_date=date_match.group(1) if date_match else None,
            retrieved_at=now_iso(),
            provider=self.name,
        )


def html_to_text(page: str) -> str:
    page = _SCRIPT_RE.sub(" ", page)
    return " ".join(html.unescape(_TAG_RE.sub(" ", page)).split())
