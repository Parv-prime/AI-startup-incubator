"""Market/competitor research must be search → evidence → analysis, and must never
let the model's unsupported claims through as research."""

from __future__ import annotations

import json

import pytest

from app.core.errors import ModelUnavailableError
from app.models.base import ModelResponse
from app.research.base import ResearchProviderError, ResearchUnavailableError, Source, now_iso
from app.research.evidence import INSUFFICIENT_EVIDENCE, NOT_VERIFIED
from app.tools.base import ToolContext
from app.tools.builtin.competitor_research import CompetitorResearchTool
from app.tools.builtin.market_research import MarketResearchTool
from app.tools.builtin.web_search import WebSearchTool

CTX = ToolContext(user_id="u", project_id="p", run_id="r")


def src(title, url, snippet, date=None, provider="tavily"):
    return Source(title=title, url=url, snippet=snippet, source_date=date, retrieved_at=now_iso(), provider=provider)


MARKET_SOURCES = [
    src(
        "India food safety testing market",
        "https://www.marketreport.example.com/india-food-safety",
        "The India food safety testing market was valued at USD 450 million in 2024. Demand is rising among restaurants.",
        date="2025-02-01",
    ),
    src("FSSAI annual report", "https://fssai.gov.in/report", "FSSAI conducted 1,20,000 inspections in 2024."),
]


class FakeResearch:
    name = "fake"

    def __init__(self, sources=None, *, unavailable=False, pages=None):
        self.sources = sources or []
        self.unavailable = unavailable
        self.pages = pages or {}
        self.queries: list[str] = []
        self.fetched: list[str] = []
        self.provider_names = ["fake"]

    async def search(self, query, max_results=5, recency_days=None, *, topic=None):
        self.queries.append(query)
        if self.unavailable:
            raise ResearchUnavailableError([ResearchProviderError("tavily", "timeout", "t")])
        return list(self.sources)

    async def fetch(self, url):
        self.fetched.append(url)
        return self.pages.get(url)


class ScriptedModel:
    name, runtime = "scripted", "test"

    def __init__(self, reply: dict | None = None, *, error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.prompts: list[str] = []

    async def health(self):
        return True

    async def chat(self, messages, tools=None, *, temperature=None, max_tokens=None):
        self.prompts.append("\n".join(m.content or "" for m in messages))
        if self.error:
            raise self.error
        return ModelResponse(content=json.dumps(self.reply))


# --------------------------------------------------------------- market research --


@pytest.mark.asyncio
async def test_market_research_is_search_then_evidence_then_analysis():
    research = FakeResearch(MARKET_SOURCES)
    model = ScriptedModel(
        {
            "summary": "Growing market.",
            "target_market": "Restaurants",
            "demand_summary": "Demand is rising among restaurants [S1].",
            "key_findings": [
                # Sources are ranked authoritative-first, so S1 = FSSAI (gov), S2 = market report.
                {"claim": "The market was valued at USD 450 million in 2024.", "source_ids": ["S2"], "type": "evidence"},
                {"claim": "FSSAI conducted 1,20,000 inspections in 2024.", "source_ids": ["S1"], "type": "evidence"},
                {"claim": "The market will reach USD 2 billion by 2030.", "source_ids": ["S2"], "type": "evidence"},
                # Right number, wrong source: must also be rejected.
                {"claim": "FSSAI conducted 1,20,000 inspections in 2024.", "source_ids": ["S2"], "type": "evidence"},
                {"claim": "Everyone needs this.", "source_ids": [], "type": "evidence"},
                {"claim": "A made-up report says so.", "source_ids": ["S7"], "type": "evidence"},
            ],
            "customer_segments": ["Cloud kitchens"],
            "trends": ["Adoption rising", "Market growing 35% a year"],
            "opportunities": ["Compliance automation"],
            "risks": ["Price sensitivity"],
            "limitations": [],
        }
    )
    tool = MarketResearchTool(model, research)
    result = await tool.run({"industry": "food safety", "focus": "market size"}, CTX)

    # search happened first, with the user's focus in a query
    assert research.queries and any("market size" in q for q in research.queries)
    # the model analysed the retrieved evidence, numbered with real URLs
    assert "[S1]" in model.prompts[0] and "https://fssai.gov.in/report" in model.prompts[0]

    claims = [f["claim"] for f in result["key_findings"]]
    assert claims == [
        "The market was valued at USD 450 million in 2024.",
        "FSSAI conducted 1,20,000 inspections in 2024.",
    ]
    finding = result["key_findings"][0]
    assert finding["source_url"] == "https://www.marketreport.example.com/india-food-safety"
    assert finding["source_date"] == "2025-02-01"
    assert "450 million" in finding["evidence"]  # a real excerpt from the source

    assert "Market growing 35% a year" not in result["trends"]  # invented figure stripped
    assert any("cited no retrieved source" in item for item in result["limitations"])
    assert any("did not appear in the cited source" in item for item in result["limitations"])

    assert result["data_available"] is True
    assert result["research_status"] == "live"
    urls = {s["url"] for s in result["sources"]}
    assert urls == {m.url for m in MARKET_SOURCES}
    assert all(s["retrieved_at"] for s in result["sources"])
    # government source ranked first
    assert result["sources"][0]["url"] == "https://fssai.gov.in/report"


@pytest.mark.asyncio
async def test_market_research_unavailable_does_not_call_llm():
    model = ScriptedModel({})
    result = await MarketResearchTool(model, FakeResearch(unavailable=True)).run({"industry": "edtech"}, CTX)
    assert model.prompts == []
    assert result["data_available"] is False
    assert result["research_status"] == "unavailable"
    assert result["note"].startswith("Live research is currently unavailable.")
    assert result["key_findings"] == [] and result["sources"] == []


@pytest.mark.asyncio
async def test_market_research_no_results_says_insufficient_evidence():
    model = ScriptedModel({})
    result = await MarketResearchTool(model, FakeResearch([])).run({"industry": "edtech"}, CTX)
    assert model.prompts == []
    assert result["research_status"] == "no_results"
    assert result["note"] == INSUFFICIENT_EVIDENCE


@pytest.mark.asyncio
async def test_market_research_background_only_when_explicitly_allowed():
    model = ScriptedModel({"target_market": "Students", "demand_summary": "General interest.", "trends": ["Online learning"]})
    result = await MarketResearchTool(model, FakeResearch(unavailable=True)).run(
        {"industry": "edtech", "allow_background_knowledge": True}, CTX
    )
    assert result["research_status"] == "background_only"
    assert result["basis"] == "background_knowledge"
    assert result["sources"] == [] and result["data_available"] is False
    assert "NOT live" in result["analysis_basis"]


@pytest.mark.asyncio
async def test_market_research_keeps_sources_when_llm_is_down():
    model = ScriptedModel(error=ModelUnavailableError("AI service is temporarily unavailable. Please try again."))
    result = await MarketResearchTool(model, FakeResearch(MARKET_SOURCES)).run({"industry": "food safety"}, CTX)
    assert result["research_status"] == "live"
    assert len(result["sources"]) == 2
    assert result["key_findings"] == []
    assert result["data_available"] is False


# ----------------------------------------------------------- competitor research --

COMPETITOR_SOURCES = [
    src(
        "Top food safety apps in India",
        "https://blog.example.com/top-apps",
        "Acme Hygiene offers kitchen monitoring for restaurants at ₹499/month. Beta Safe targets hotels.",
    ),
]
ACME_PAGE = src(
    "Acme Hygiene - Kitchen monitoring",
    "https://acmehygiene.example.com/",
    "Acme Hygiene: automated kitchen hygiene monitoring. Plans from ₹499/month.",
    provider="jina",
)


@pytest.mark.asyncio
async def test_competitor_research_verifies_names_sites_and_pricing():
    research = FakeResearch(COMPETITOR_SOURCES, pages={"https://acmehygiene.example.com": ACME_PAGE})
    model = ScriptedModel(
        {
            "competitors": [
                {
                    "name": "Acme Hygiene",
                    "website": "acmehygiene.example.com",
                    "product": "Kitchen monitoring",
                    "target_audience": "Restaurants",
                    "pricing": "₹499/month",
                    "features": ["Automated monitoring"],
                    "strengths": ["Focused"],
                    "weaknesses": ["Small"],
                    "positioning": "Restaurant hygiene",
                    "source_ids": ["S1"],
                },
                {
                    "name": "Beta Safe",
                    "website": "https://betasafe.example.com",
                    "product": "Hotel safety",
                    "pricing": "₹1,999/month",
                    "source_ids": ["S1"],
                },
                {"name": "Ghost Corp", "product": "Invented", "pricing": "₹10/month", "source_ids": ["S1"]},
            ],
            "differentiation_opportunity": "Focus on cloud kitchens.",
            "limitations": [],
        }
    )
    result = await CompetitorResearchTool(model, research).run({"industry": "food safety"}, CTX)

    names = [c["name"] for c in result["competitors"]]
    assert names == ["Acme Hygiene", "Beta Safe"]  # Ghost Corp is in no source → dropped
    acme, beta = result["competitors"]

    assert acme["website_verified"] is True
    assert acme["website"] == "https://acmehygiene.example.com/"
    assert acme["pricing"] == "₹499/month" and acme["pricing_verified"] is True
    assert "https://acmehygiene.example.com/" in acme["source_urls"]

    assert beta["pricing"] == NOT_VERIFIED and beta["pricing_verified"] is False
    assert beta["website"] is None and beta["website_verified"] is False

    assert "https://acmehygiene.example.com" in research.fetched
    assert any("no retrieved source mentions them" in item for item in result["limitations"])
    assert {s["url"] for s in result["sources"]} == {
        "https://blog.example.com/top-apps",
        "https://acmehygiene.example.com/",
    }


@pytest.mark.asyncio
async def test_competitor_research_unavailable():
    model = ScriptedModel({})
    result = await CompetitorResearchTool(model, FakeResearch(unavailable=True)).run({"industry": "x"}, CTX)
    assert model.prompts == []
    assert result["competitors"] == []
    assert result["note"].startswith("Live research is currently unavailable.")


# ------------------------------------------------------------------- web search --


@pytest.mark.asyncio
async def test_web_search_tool_returns_structured_sources():
    result = await WebSearchTool(FakeResearch(MARKET_SOURCES)).run({"query": "food safety India"}, CTX)
    assert result["research_status"] == "live"
    assert result["provider"] == "tavily"
    assert result["sources"][0]["url"] == "https://fssai.gov.in/report"
    assert result["sources"][0]["source_kind"] == "government"


@pytest.mark.asyncio
async def test_web_search_tool_unavailable():
    result = await WebSearchTool(FakeResearch(unavailable=True)).run({"query": "x"}, CTX)
    assert result["data_available"] is False
    assert result["note"].startswith("Live research is currently unavailable.")


@pytest.mark.asyncio
async def test_llm_sees_compact_research_result():
    tool = MarketResearchTool(ScriptedModel({"key_findings": []}), FakeResearch(MARKET_SOURCES))
    full = await tool.run({"industry": "food safety"}, CTX)
    view = tool.model_view(full)
    assert all(set(s) == {"id", "title", "url", "source_date"} for s in view["sources"])
    assert "snippet" in full["sources"][0]  # the persisted/UI result keeps the excerpts


@pytest.mark.asyncio
async def test_competitor_research_reads_top_result_pages_before_analysis():
    listing = src("Top food safety startups", "https://list.example.com/top", "A list of startups.")
    full_page = src("Top food safety startups", "https://list.example.com/top", "1. Acme Hygiene — kitchen monitoring.", provider="jina")
    full_page.content = "1. Acme Hygiene — kitchen monitoring for restaurants."
    research = FakeResearch([listing], pages={"https://list.example.com/top": full_page})
    model = ScriptedModel({"competitors": [{"name": "Acme Hygiene", "product": "Kitchen monitoring", "source_ids": ["S1"]}]})
    result = await CompetitorResearchTool(model, research).run({"industry": "food safety"}, CTX)
    assert research.fetched[0] == "https://list.example.com/top"
    assert "Acme Hygiene" in model.prompts[0]  # full page text reached the analysis
    assert [c["name"] for c in result["competitors"]] == ["Acme Hygiene"]
