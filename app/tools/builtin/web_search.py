from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.research.base import ResearchProvider
from app.research.evidence import UNAVAILABLE_NOTE, describe_age, gather_evidence
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel

_NO_RESULTS_NOTE = (
    "No live search results were found for this query. Do not invent a real-world figure — "
    "tell the founder you could not verify this and clearly label any number you give as an estimate."
)
_LIVE_NOTE = (
    "Live web search results. Only state facts that appear in these snippets, cite the source "
    "title/URL for each one, and never add URLs that are not listed here."
)


class WebSearchInput(BaseModel):
    query: str = Field(
        description="A specific, real-world search query, e.g. 'AWS EC2 t3.micro price India', "
        "'average React developer salary Bangalore 2025', 'Razorpay payment gateway fees India'."
    )
    max_results: int = Field(default=5, ge=1, le=10)
    recency_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="Only return results published within this many days (for recent news/prices).",
    )
    news: bool = Field(default=False, description="Search news coverage instead of the general web.")


class WebSearchSource(BaseModel):
    id: str
    title: str
    url: str
    domain: str
    snippet: str
    source_date: str | None = None
    retrieved_at: str
    provider: str
    source_type: str
    source_kind: str


class WebSearchOutput(BaseModel):
    query: str
    data_available: bool
    research_status: Literal["live", "no_results", "unavailable"]
    provider: str | None = None
    retrieved_at: str | None = None
    sources: list[WebSearchSource]
    note: str


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the live web for real, current information — pricing, costs, salaries, exchange "
        "rates, regulations, recent news, or anything else that must be grounded in reality instead "
        "of guessed. Returns real titles, URLs, dates and text snippets from live search results. "
        "Use only facts found in the snippets and cite their URLs; never fall back to a guessed "
        "number when this tool succeeded, and never invent sources."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = WebSearchInput
    output_model = WebSearchOutput

    def __init__(self, research: ResearchProvider):
        self.research = research

    async def execute(self, payload: WebSearchInput, context: ToolContext) -> dict[str, Any]:
        evidence = await gather_evidence(
            self.research,
            [payload.query],
            max_results=payload.max_results,
            max_sources=payload.max_results,
            recency_days=payload.recency_days,
            topic="news" if payload.news else None,
        )
        if evidence.status == "unavailable":
            note = UNAVAILABLE_NOTE
        elif evidence.status == "no_results":
            note = _NO_RESULTS_NOTE
        else:
            note = f"{_LIVE_NOTE} {describe_age(evidence.retrieved_at)}".strip()
        return {
            "query": payload.query,
            "data_available": evidence.status == "live",
            "research_status": evidence.status,
            "provider": ", ".join(evidence.providers) or None,
            "retrieved_at": evidence.retrieved_at,
            "sources": evidence.to_dicts(),
            "note": note,
        }
