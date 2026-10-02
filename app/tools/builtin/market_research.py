from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.models.base import ModelProvider
from app.models.structured import generate_json
from app.tools.base import BaseTool, ToolContext
from app.tools.builtin.web_search import run_search
from app.tools.permissions import PermissionLevel

SYSTEM_PROMPT = """You are a market research analyst assisting a startup founder.

If live web search notes are provided below, ground your answer in them — use the real market
size figures, statistics, and trends they contain, and set "data_available" to true.

Otherwise, you have NO access to live internet data, current statistics, or real-time sources:
provide a qualitative analysis based on general background knowledge only, never invent specific
market-size numbers, revenue figures, or growth percentages (describe demand, trends,
opportunities, and risks in qualitative terms instead), and set "data_available" to false.

Respond with ONLY a JSON object with exactly these keys:
{
  "data_available": boolean,
  "target_market": string,
  "demand_summary": string,
  "customer_segments": [string, ...],
  "trends": [string, ...],
  "opportunities": [string, ...],
  "risks": [string, ...]
}
"""


class MarketResearchInput(BaseModel):
    industry: str = Field(description="The startup's industry or category.")
    problem: str | None = Field(default=None, description="The problem the startup addresses.")
    target_customer: str | None = Field(default=None, description="Who the startup serves.")
    geography: str | None = Field(default=None, description="Target market geography, if known.")
    research_notes: str | None = Field(
        default=None,
        description="Real findings already gathered from the web_search tool (titles/snippets "
        "about actual market size, stats, trends, etc). When provided, ground the analysis in "
        "these instead of general background knowledge.",
    )


class MarketResearchOutput(BaseModel):
    data_available: bool
    target_market: str
    demand_summary: str
    customer_segments: list[str]
    trends: list[str]
    opportunities: list[str]
    risks: list[str]
    sources: list[dict]
    note: str


class MarketResearchTool(BaseTool):
    name = "market_research"
    description = (
        "Analyze market demand, target customers, trends, opportunities, and risks for a "
        "startup idea. Use when the user asks about market size, demand, target customers, "
        "or industry trends. Returns qualitative analysis, not live/current data."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = MarketResearchInput
    output_model = MarketResearchOutput

    def __init__(self, model: ModelProvider):
        self.model = model

    async def execute(self, payload: MarketResearchInput, context: ToolContext) -> dict[str, Any]:
        geography = payload.geography or "India"
        search = await run_search(f"{payload.industry} market size demand trends {geography}", max_results=5)
        sources: list[dict] = []
        notes = payload.research_notes or ""
        if search["data_available"]:
            found = "\n".join(f"- {r['title']}: {r['snippet']}" for r in search["results"])
            notes = f"{notes}\n{found}".strip()
            now = datetime.now(timezone.utc).isoformat()
            sources = [
                {"title": r["title"], "url": r["url"], "source_type": "web_search", "retrieved_at": now}
                for r in search["results"]
            ]

        user_prompt = (
            f"Industry: {payload.industry}\n"
            f"Problem: {payload.problem or 'unspecified'}\n"
            f"Target customer: {payload.target_customer or 'unspecified'}\n"
            f"Geography: {geography}\n"
        )
        if notes:
            user_prompt += f"\nLive web search notes:\n{notes}\n"
        parsed = await generate_json(self.model, system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

        if parsed is None:
            return _fallback(payload)

        data_available = bool(parsed.get("data_available")) and bool(notes)
        return {
            "data_available": data_available,
            "target_market": str(parsed.get("target_market") or payload.target_customer or "Unspecified"),
            "demand_summary": str(parsed.get("demand_summary") or "Not enough information to assess demand."),
            "customer_segments": _as_str_list(parsed.get("customer_segments")),
            "trends": _as_str_list(parsed.get("trends")),
            "opportunities": _as_str_list(parsed.get("opportunities")),
            "risks": _as_str_list(parsed.get("risks")),
            "sources": sources if data_available else [],
            "note": (
                "Grounded in live web search results."
                if data_available
                else "Based on the model's general background knowledge, not live market data. "
                "No current statistics, sizing, or sources were retrieved (no internet, or nothing found)."
            ),
        }


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _fallback(payload: MarketResearchInput) -> dict[str, Any]:
    return {
        "data_available": False,
        "target_market": payload.target_customer or "Unspecified",
        "demand_summary": "The model could not produce a structured analysis for this request.",
        "customer_segments": [],
        "trends": [],
        "opportunities": [],
        "risks": [],
        "sources": [],
        "note": "Analysis unavailable: the model response could not be parsed.",
    }
