from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.config.settings import Settings
from app.research import cache as cache_module
from app.research.base import ResearchProviderError, ResearchUnavailableError, Source, now_iso
from app.research.cache import CachedResearchProvider
from app.research.evidence import EvidenceSet, describe_age, gather_evidence, numbers_supported
from app.research.factory import create_research_provider
from app.research.fallback import FallbackResearchProvider
from app.research.providers.duckduckgo import DuckDuckGoProvider, parse_results
from app.research.providers.exa import ExaProvider
from app.research.providers.tavily import TavilyProvider
from app.research.reader import is_safe_public_url

TAVILY_OK = {
    "query": "q",
    "results": [
        {
            "title": "Food safety market report",
            "url": "https://www.example.gov.in/report",
            "content": "The market was valued at 1,250 crore in 2025.",
            "score": 0.9,
            "published_date": "Tue, 11 Mar 2025 17:00:00 GMT",
        },
        {"title": "No date article", "url": "https://news.example.com/a", "content": "Some text."},
    ],
}
EXA_OK = {
    "results": [
        {
            "title": "Exa result",
            "url": "https://exa-found.example.com/page",
            "publishedDate": "2025-06-01T00:00:00.000Z",
            "text": "Exa page text.",
        }
    ]
}
DDG_HTML = """
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fddg-found.example.com%2Fx&amp;rut=1">DDG <b>Result</b></a>
<a class="result__snippet" href="#">A <b>snippet</b> from DuckDuckGo.</a>
"""


def _mock(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def _router(tavily=None, exa=None, ddg=None, calls=None):
    """Route mocked HTTP calls per provider host. Each value is (status, body) or an exception."""

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if calls is not None:
            calls.append(host)
        spec = {"api.tavily.com": tavily, "api.exa.ai": exa, "html.duckduckgo.com": ddg}.get(host)
        if spec is None:
            return httpx.Response(404)
        if isinstance(spec, Exception):
            raise spec
        status, body = spec
        if isinstance(body, str):
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=body)

    return handler


def _chain():
    return FallbackResearchProvider(
        [TavilyProvider(api_key="tvly-test"), ExaProvider(api_key="exa-test"), DuckDuckGoProvider()]
    )


# ------------------------------------------------------------------ providers --


@pytest.mark.asyncio
async def test_tavily_success_preserves_urls_dates_and_timestamp(monkeypatch):
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=TAVILY_OK)

    _mock(monkeypatch, handler)
    results = await TavilyProvider(api_key="tvly-test").search("food safety India", 5, 30, topic="news")
    assert seen["auth"] == "Bearer tvly-test"
    assert seen["body"]["topic"] == "news" and seen["body"]["time_range"] == "month"
    assert seen["body"]["search_depth"] == "basic"
    assert [r.url for r in results] == ["https://www.example.gov.in/report", "https://news.example.com/a"]
    assert results[0].source_date == "Tue, 11 Mar 2025 17:00:00 GMT"
    assert results[1].source_date is None  # never invented
    assert results[0].provider == "tavily"
    datetime.fromisoformat(results[0].retrieved_at)


@pytest.mark.asyncio
async def test_tavily_failure_falls_back_to_exa(monkeypatch):
    _mock(monkeypatch, _router(tavily=(429, {"detail": "limit"}), exa=(200, EXA_OK)))
    results = await _chain().search("q")
    assert results[0].provider == "exa"
    assert results[0].url == "https://exa-found.example.com/page"
    assert results[0].source_date == "2025-06-01T00:00:00.000Z"


@pytest.mark.asyncio
async def test_tavily_and_exa_failure_falls_back_to_duckduckgo(monkeypatch):
    _mock(
        monkeypatch,
        _router(
            tavily=httpx.ConnectTimeout("t"),
            exa=(401, {"error": "bad key"}),
            ddg=(200, DDG_HTML),
        ),
    )
    results = await _chain().search("q")
    assert results[0].provider == "duckduckgo"
    assert results[0].url == "https://ddg-found.example.com/x"
    assert results[0].title == "DDG Result"


@pytest.mark.asyncio
async def test_all_providers_unavailable(monkeypatch):
    _mock(
        monkeypatch,
        _router(tavily=(500, {}), exa=httpx.ConnectError("down"), ddg=(202, "anomaly-modal")),
    )
    with pytest.raises(ResearchUnavailableError) as info:
        await _chain().search("q")
    kinds = {f.provider: f.kind for f in info.value.failures}
    assert kinds == {"tavily": "http", "exa": "network", "duckduckgo": "rate_limit"}


@pytest.mark.asyncio
async def test_malformed_response_falls_through(monkeypatch):
    _mock(monkeypatch, _router(tavily=(200, {"results": "nope"}), exa=(200, EXA_OK)))
    results = await _chain().search("q")
    assert results[0].provider == "exa"


@pytest.mark.asyncio
async def test_empty_results_everywhere_returns_empty_list(monkeypatch):
    _mock(monkeypatch, _router(tavily=(200, {"results": []}), exa=(200, {"results": []}), ddg=(200, "<html></html>")))
    assert await _chain().search("q") == []


@pytest.mark.asyncio
async def test_no_configured_providers_means_unavailable():
    with pytest.raises(ResearchUnavailableError):
        await FallbackResearchProvider([]).search("q")


def test_factory_skips_providers_without_keys():
    settings = Settings(_env_file=None, research_provider="tavily", research_fallback_providers="exa,duckduckgo")
    chain = create_research_provider(settings)
    assert chain.provider_names == ["duckduckgo"]

    settings = Settings(_env_file=None, tavily_api_key="tvly-x", exa_api_key="exa-x")
    assert create_research_provider(settings).provider_names == ["exa", "tavily", "duckduckgo"]


def test_duckduckgo_parser_resolves_redirect_urls():
    results = parse_results(DDG_HTML, limit=5)
    assert results[0].url == "https://ddg-found.example.com/x"
    assert results[0].snippet == "A snippet from DuckDuckGo."
    assert results[0].source_date is None


# ---------------------------------------------------------------------- cache --


class CountingProvider:
    name = "counting"

    def __init__(self):
        self.calls = 0

    async def search(self, query, max_results=5, recency_days=None, *, topic=None):
        self.calls += 1
        return [Source(title="t", url="https://x.example.com", retrieved_at=now_iso(), provider="tavily")]

    async def fetch(self, url):
        return None


@pytest.mark.asyncio
async def test_cache_hit_keeps_original_retrieval_time():
    inner = CountingProvider()
    cached = CachedResearchProvider(inner, ttl_seconds=3600)
    first = await cached.search("Food Safety")
    second = await cached.search("  food   safety ")
    assert inner.calls == 1
    assert second[0].retrieved_at == first[0].retrieved_at


@pytest.mark.asyncio
async def test_cache_expires(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: clock[0])
    inner = CountingProvider()
    cached = CachedResearchProvider(inner, ttl_seconds=60)
    await cached.search("q")
    clock[0] += 30
    await cached.search("q")
    assert inner.calls == 1
    clock[0] += 61
    await cached.search("q")
    assert inner.calls == 2


# ------------------------------------------------------------------- evidence --


@pytest.mark.asyncio
async def test_gather_evidence_dedupes_and_ranks_government_first():
    class Fixed:
        name = "fixed"

        async def search(self, query, max_results=5, recency_days=None, *, topic=None):
            return [
                Source(title="Blog", url="https://blog.example.com/a", retrieved_at=now_iso(), provider="tavily"),
                Source(title="Gov", url="https://fssai.gov.in/x", retrieved_at=now_iso(), provider="tavily"),
            ]

        async def fetch(self, url):
            return None

    evidence = await gather_evidence(Fixed(), ["a", "b"], max_results=5, max_sources=5)
    assert evidence.status == "live"
    assert [s.title for s in evidence.sources] == ["Gov", "Blog"]


@pytest.mark.asyncio
async def test_gather_evidence_unavailable():
    class Down:
        name = "down"

        async def search(self, *args, **kwargs):
            raise ResearchUnavailableError([ResearchProviderError("tavily", "timeout", "t")])

        async def fetch(self, url):
            return None

    evidence = await gather_evidence(Down(), ["a"], max_results=5, max_sources=5)
    assert evidence.status == "unavailable"
    assert evidence.sources == []


def test_citation_ids_must_exist():
    evidence = EvidenceSet(
        queries=["q"],
        sources=[Source(title="A", url="https://a.example.com", retrieved_at=now_iso(), provider="tavily")],
        status="live",
    )
    assert evidence.valid_ids(["S1", "[S1]", "S2", "S9", "garbage"]) == ["S1"]


def test_numbers_supported():
    assert numbers_supported("Market worth 1,250 crore in 2025", ["valued at 1250 crore in 2025"])
    assert not numbers_supported("Market worth 9,999 crore", ["valued at 1250 crore"])
    assert numbers_supported("Top 3 players", ["no numbers here"])  # single digits ignored


def test_describe_age():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert describe_age((now - timedelta(minutes=42)).isoformat(), now=now) == "Retrieved approximately 42 minutes ago."
    assert describe_age(now.isoformat(), now=now) == "Retrieved just now."


@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://example.com/pricing", True),
        ("http://localhost:11434/api", False),
        ("http://127.0.0.1/", False),
        ("http://10.0.0.5/admin", False),
        ("file:///etc/passwd", False),
        ("https://8.8.8.8/", True),
    ],
)
def test_only_public_urls_are_fetched(url, ok):
    assert is_safe_public_url(url) is ok


def test_words_supported():
    from app.research.evidence import words_supported

    assert words_supported("Automated kitchen monitoring", ["Acme offers automated kitchen hygiene monitoring."])
    assert not words_supported("Blockchain supplier tokenization", ["Acme offers kitchen monitoring."])
