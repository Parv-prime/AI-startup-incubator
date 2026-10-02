from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.models.base import ModelProvider
from app.models.structured import generate_json
from app.tools.base import BaseTool, ToolContext
from app.tools.builtin.web_search import run_search
from app.tools.permissions import PermissionLevel

SYSTEM_PROMPT = """You are a competitive-analysis analyst assisting a startup founder.

If live web search notes are provided below, ground your answer in them — use the real
competitor names, pricing, and details they contain, and set "data_available" to true.

Otherwise, you have NO access to live internet data or current pricing/statistics: name only
real, well-known companies/products you are reasonably confident exist in this space based on
general background knowledge, do NOT invent fictional competitors, exact pricing, or exact
user/revenue numbers, and set "data_available" to false. If you are not confident a competitor
is real, omit it. If you cannot name any real competitors confidently, return an empty
competitors list.

Respond with ONLY a JSON object with exactly this shape:
{
  "data_available": boolean,
  "competitors": [
    {
      "name": string,
      "product": string,
      "target_audience": string,
      "pricing": string or null,
      "strengths": [string, ...],
      "weaknesses": [string, ...],
      "positioning": string
    }
  ],
  "differentiation_opportunity": string
}
"""


class CompetitorResearchInput(BaseModel):
    industry: str = Field(description="The startup's industry or category.")
    solution: str | None = Field(default=None, description="What the startup's product/solution does.")
    target_customer: str | None = Field(default=None, description="Who the startup serves.")
    research_notes: str | None = Field(
        default=None,
        description="Real findings already gathered from the web_search tool (titles/snippets "
        "about actual competitors, their pricing, etc). When provided, ground the analysis in "
        "these instead of general background knowledge.",
    )


class Competitor(BaseModel):
    name: str
    product: str
    target_audience: str
    pricing: str | None = None
    strengths: list[str]
    weaknesses: list[str]
    positioning: str


class CompetitorResearchOutput(BaseModel):
    data_available: bool
    competitors: list[Competitor]
    differentiation_opportunity: str
    sources: list[dict]
    note: str


class CompetitorResearchTool(BaseTool):
    name = "competitor_research"
    description = (
        "Identify known competitors for a startup idea, their positioning, strengths, "
        "weaknesses, and a differentiation opportunity. Use when the user asks about "
        "competitors, competition, or alternatives."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = CompetitorResearchInput
    output_model = CompetitorResearchOutput

    def __init__(self, model: ModelProvider):
        self.model = model

    async def execute(self, payload: CompetitorResearchInput, context: ToolContext) -> dict[str, Any]:
        search = await run_search(f"top {payload.industry} startups companies competitors India", max_results=5)
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
            f"Solution: {payload.solution or 'unspecified'}\n"
            f"Target customer: {payload.target_customer or 'unspecified'}\n"
        )
        if notes:
            user_prompt += f"\nLive web search notes:\n{notes}\n"
        parsed = await generate_json(self.model, system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

        if parsed is None:
            return _fallback()

        competitors = []
        for item in parsed.get("competitors") or []:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            competitors.append(
                {
                    "name": str(item.get("name")),
                    "product": str(item.get("product") or ""),
                    "target_audience": str(item.get("target_audience") or ""),
                    "pricing": item.get("pricing") if item.get("pricing") else None,
                    "strengths": _as_str_list(item.get("strengths")),
                    "weaknesses": _as_str_list(item.get("weaknesses")),
                    "positioning": str(item.get("positioning") or ""),
                }
            )

        data_available = bool(parsed.get("data_available")) and bool(notes)
        return {
            "data_available": data_available,
            "competitors": competitors,
            "differentiation_opportunity": str(
                parsed.get("differentiation_opportunity")
                or "Not enough information to identify a clear differentiation angle."
            ),
            "sources": sources if data_available else [],
            "note": (
                "Grounded in live web search results."
                if data_available
                else "Based on the model's general background knowledge of well-known players, "
                "not a live competitor/pricing lookup (no internet, or nothing found)."
            ),
        }


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _fallback() -> dict[str, Any]:
    return {
        "data_available": False,
        "competitors": [],
        "differentiation_opportunity": "Analysis unavailable: the model response could not be parsed.",
        "sources": [],
        "note": "Analysis unavailable: the model response could not be parsed.",
    }
