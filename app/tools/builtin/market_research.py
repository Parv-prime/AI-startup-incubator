from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.base import ModelProvider
from app.research.base import ResearchProvider
from app.research.evidence import (
    INSUFFICIENT_EVIDENCE,
    UNAVAILABLE_NOTE,
    EvidenceSet,
    compact_research_result,
    describe_age,
    gather_evidence,
    numbers_supported,
)
from app.research.synthesis import (
    GROUNDING_RULES,
    as_str_list,
    filter_unsupported_numbers,
    safe_generate_json,
    validate_findings,
)
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel

SYSTEM_PROMPT = f"""You are a market research analyst assisting a startup founder. You are given
numbered sources that were just retrieved from the live web.

{GROUNDING_RULES}

Respond with ONLY a JSON object with exactly these keys:
{{
  "summary": string,                      // 2-3 sentence research summary
  "target_market": string,
  "demand_summary": string,               // source-backed where possible; say if not
  "key_findings": [
    {{"claim": string, "source_ids": ["S1"], "type": "evidence" or "derived"}}
  ],
  "customer_segments": [string, ...],     // your interpretation
  "trends": [string, ...],                // your interpretation of the sources
  "opportunities": [string, ...],         // your interpretation
  "risks": [string, ...],                 // your interpretation
  "limitations": [string, ...]            // gaps, old sources, weak evidence
}}
"""

BACKGROUND_PROMPT = """You are a market research analyst assisting a startup founder.
Live research is NOT available. Give a short qualitative overview from general background
knowledge only. Do NOT give specific market sizes, revenue figures, growth percentages, prices or
dates, do not name sources, and do not present anything as current.

Respond with ONLY a JSON object with exactly these keys:
{
  "target_market": string,
  "demand_summary": string,
  "customer_segments": [string, ...],
  "trends": [string, ...],
  "opportunities": [string, ...],
  "risks": [string, ...]
}
"""

_ANALYSIS_BASIS = "AI interpretation of the retrieved sources — not itself a source."


class MarketResearchInput(BaseModel):
    industry: str = Field(description="The startup's industry or category.")
    problem: str | None = Field(default=None, description="The problem the startup addresses.")
    target_customer: str | None = Field(default=None, description="Who the startup serves.")
    geography: str | None = Field(default=None, description="Target market geography, if known.")
    focus: str | None = Field(
        default=None,
        description="The specific thing the user asked to research, e.g. 'market size', "
        "'regulations', 'pricing', 'recent news', 'customer segments'. Taken from the user's request.",
    )
    allow_background_knowledge: bool = Field(
        default=False,
        description="Set true ONLY if the user explicitly asked for general/background information "
        "rather than current research. Allows a clearly-labelled non-live overview when live "
        "research is unavailable.",
    )


class Finding(BaseModel):
    claim: str
    type: Literal["evidence", "derived"]
    evidence: str
    source_ids: list[str]
    source_title: str | None = None
    source_url: str | None = None
    source_date: str | None = None


class MarketResearchOutput(BaseModel):
    data_available: bool
    research_status: Literal["live", "no_results", "unavailable", "background_only"]
    basis: Literal["retrieved_evidence", "background_knowledge", "none"]
    summary: str
    target_market: str
    demand_summary: str
    key_findings: list[Finding]
    customer_segments: list[str]
    trends: list[str]
    opportunities: list[str]
    risks: list[str]
    analysis_basis: str
    limitations: list[str]
    queries: list[str]
    provider: str | None = None
    retrieved_at: str | None = None
    sources: list[dict]
    note: str


class MarketResearchTool(BaseTool):
    name = "market_research"
    description = (
        "Live, evidence-based market research: searches the web for current sources (market size, "
        "growth, trends, customer segments, pricing, regulations, recent developments), then "
        "analyses ONLY that evidence and returns cited findings with source URLs and dates. Use "
        "when the user asks about market size, demand, target customers, industry trends or "
        "current market conditions. Pass the user's specific question as 'focus'."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = MarketResearchInput
    output_model = MarketResearchOutput

    def __init__(
        self,
        model: ModelProvider,
        research: ResearchProvider,
        *,
        max_results: int = 5,
        max_sources: int = 6,
        prompt_chars_per_source: int = 700,
    ):
        self.model = model
        self.research = research
        self.max_results = max_results
        self.max_sources = max_sources
        self.prompt_chars_per_source = prompt_chars_per_source

    def model_view(self, result: dict[str, Any]) -> dict[str, Any]:
        return compact_research_result(result)

    async def execute(self, payload: MarketResearchInput, context: ToolContext) -> dict[str, Any]:
        geography = payload.geography or "India"
        queries = build_queries(payload, geography)
        evidence = await gather_evidence(
            self.research, queries, max_results=self.max_results, max_sources=self.max_sources
        )
        if evidence.status != "live":
            return await self._without_evidence(payload, evidence)

        user_prompt = (
            f"Industry: {payload.industry}\n"
            f"Problem: {payload.problem or 'unspecified'}\n"
            f"Target customer: {payload.target_customer or 'unspecified'}\n"
            f"Geography: {geography}\n"
            f"Research focus: {payload.focus or 'overall market'}\n"
            f"Today's date: {datetime.now(timezone.utc).date().isoformat()}\n\n"
            f"SOURCES:\n{evidence.prompt_block(max_chars_per_source=self.prompt_chars_per_source)}\n"
        )
        parsed, model_error = await safe_generate_json(
            self.model, system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, max_tokens=1200
        )
        return _from_evidence(payload, evidence, parsed, model_error)

    async def _without_evidence(self, payload: MarketResearchInput, evidence: EvidenceSet) -> dict[str, Any]:
        headline = UNAVAILABLE_NOTE if evidence.status == "unavailable" else INSUFFICIENT_EVIDENCE
        result = _empty(payload, evidence, headline)
        if not payload.allow_background_knowledge:
            return result

        parsed, _ = await safe_generate_json(
            self.model,
            system_prompt=BACKGROUND_PROMPT,
            user_prompt=f"Industry: {payload.industry}\nProblem: {payload.problem or 'unspecified'}\n"
            f"Target customer: {payload.target_customer or 'unspecified'}\n",
        )
        if not parsed:
            return result
        result.update(
            research_status="background_only",
            basis="background_knowledge",
            target_market=str(parsed.get("target_market") or result["target_market"]),
            demand_summary=str(parsed.get("demand_summary") or result["demand_summary"]),
            customer_segments=as_str_list(parsed.get("customer_segments")),
            trends=as_str_list(parsed.get("trends")),
            opportunities=as_str_list(parsed.get("opportunities")),
            risks=as_str_list(parsed.get("risks")),
            analysis_basis="General background knowledge of the AI model — NOT live or current research.",
            note=f"{headline} The overview below is general background knowledge only.",
        )
        return result


def build_queries(payload: MarketResearchInput, geography: str) -> list[str]:
    year = datetime.now(timezone.utc).year
    industry = payload.industry.strip()
    queries: list[str] = []
    if payload.focus:
        queries.append(f"{industry} {payload.focus} {geography}")
    queries.append(f"{industry} market size {geography} {year}")
    queries.append(f"{industry} industry trends growth {geography}")
    if payload.target_customer:
        queries.append(f"{industry} {payload.target_customer} demand {geography}")
    return queries[:3]


def _empty(payload: MarketResearchInput, evidence: EvidenceSet, headline: str) -> dict[str, Any]:
    return {
        "data_available": False,
        "research_status": evidence.status,
        "basis": "none",
        "summary": headline,
        "target_market": payload.target_customer or "Unspecified",
        "demand_summary": headline,
        "key_findings": [],
        "customer_segments": [],
        "trends": [],
        "opportunities": [],
        "risks": [],
        "analysis_basis": "No analysis was produced because no evidence was retrieved.",
        "limitations": [headline],
        "queries": evidence.queries,
        "provider": None,
        "retrieved_at": None,
        "sources": [],
        "note": headline,
    }


def _from_evidence(
    payload: MarketResearchInput,
    evidence: EvidenceSet,
    parsed: dict[str, Any] | None,
    model_error: str | None,
) -> dict[str, Any]:
    age = describe_age(evidence.retrieved_at)
    base = {
        "research_status": "live",
        "basis": "retrieved_evidence",
        "queries": evidence.queries,
        "provider": ", ".join(evidence.providers),
        "retrieved_at": evidence.retrieved_at,
        "sources": evidence.to_dicts(),
        "analysis_basis": _ANALYSIS_BASIS,
    }
    if parsed is None:
        reason = model_error or "the AI analysis could not be parsed"
        return {
            **_empty(payload, evidence, f"Sources were retrieved, but {reason.rstrip('.')}."),
            **base,
            "summary": "Live sources were retrieved (listed below) but could not be analysed. "
            "Open the sources to read the evidence directly.",
            "limitations": [f"AI analysis unavailable: {reason}"],
            "note": f"Live sources retrieved; AI analysis unavailable. {age}".strip(),
        }

    findings, limitations = validate_findings(parsed.get("key_findings"), evidence)
    dropped_total = 0
    lists: dict[str, list[str]] = {}
    for key in ("customer_segments", "trends", "opportunities", "risks"):
        lists[key], dropped = filter_unsupported_numbers(as_str_list(parsed.get(key)), evidence)
        dropped_total += dropped
    if dropped_total:
        limitations.append(
            f"{dropped_total} analysis point(s) were removed because they contained figures not found in any source."
        )
    # Free-text summaries get the same figure check as findings.
    all_text = [s.text for s in evidence.sources]
    summary = str(parsed.get("summary") or "").strip()
    demand = str(parsed.get("demand_summary") or "").strip()
    if summary and not numbers_supported(summary, all_text):
        summary = ""
        limitations.append("The AI summary was replaced because it contained figures not found in any source.")
    if demand and not numbers_supported(demand, all_text):
        demand = ""
        limitations.append("The demand summary was replaced because it contained figures not found in any source.")

    limitations = as_str_list(parsed.get("limitations")) + limitations
    if not findings:
        limitations.insert(0, INSUFFICIENT_EVIDENCE)

    undated = sum(1 for s in evidence.sources if not s.source_date)
    if undated:
        limitations.append(f"{undated} of {len(evidence.sources)} sources have no publication date available.")

    return {
        **base,
        "data_available": bool(findings),
        "summary": summary or "See key findings and sources below.",
        "target_market": str(parsed.get("target_market") or payload.target_customer or "Unspecified"),
        "demand_summary": demand or INSUFFICIENT_EVIDENCE,
        "key_findings": findings,
        **lists,
        "limitations": limitations,
        "note": (
            f"Evidence-based: {len(findings)} cited finding(s) from {len(evidence.sources)} live source(s). {age}"
            if findings
            else f"Live sources were retrieved, but no claims could be verified against them. {age}"
        ).strip(),
    }
