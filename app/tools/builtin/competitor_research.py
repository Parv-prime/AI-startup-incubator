from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.base import ModelProvider
from app.research.base import ResearchProvider, Source, domain_of
from app.research.evidence import (
    INSUFFICIENT_EVIDENCE,
    NOT_VERIFIED,
    UNAVAILABLE_NOTE,
    EvidenceSet,
    compact_research_result,
    describe_age,
    gather_evidence,
    numbers_supported,
    words_supported,
)
from app.research.reader import is_safe_public_url
from app.research.synthesis import (
    GROUNDING_RULES,
    as_str_list,
    safe_generate_json,
)
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel

SYSTEM_PROMPT = f"""You are a competitive-analysis analyst assisting a startup founder. You are given
numbered sources that were just retrieved from the live web.

{GROUNDING_RULES}
- Only list companies/products that are actually named in the sources.
- For pricing, customers, features or availability not stated in the sources, use null / empty
  lists. Never guess a price.

Respond with ONLY a JSON object with exactly this shape:
{{
  "competitors": [
    {{
      "name": string,
      "website": string or null,          // official site, only if it appears in the sources
      "product": string,
      "target_audience": string or null,
      "pricing": string or null,          // exactly as stated in a source, else null
      "features": [string, ...],
      "geography": string or null,
      "business_model": string or null,
      "strengths": [string, ...],         // your interpretation
      "weaknesses": [string, ...],        // your interpretation
      "positioning": string,              // your interpretation
      "source_ids": ["S1", ...]
    }}
  ],
  "differentiation_opportunity": string,  // your interpretation
  "limitations": [string, ...]
}}
"""

_PRICING_WORDS = ("free", "freemium", "trial", "subscription", "per month", "/month", "per user", "contact sales", "custom pricing")
_NAME_TOKEN_RE = re.compile(r"[a-z0-9]+")
_GENERIC_NAME_WORDS = {"the", "inc", "ltd", "llc", "pvt", "private", "limited", "technologies", "technology", "app", "ai", "labs", "co"}


class CompetitorResearchInput(BaseModel):
    industry: str = Field(description="The startup's industry or category.")
    solution: str | None = Field(default=None, description="What the startup's product/solution does.")
    target_customer: str | None = Field(default=None, description="Who the startup serves.")
    geography: str | None = Field(default=None, description="Target market geography, if known.")
    known_competitors: list[str] = Field(
        default_factory=list,
        description="Competitor names the user explicitly mentioned and wants researched.",
    )


class Competitor(BaseModel):
    name: str
    website: str | None = None
    website_verified: bool = False
    product: str
    target_audience: str
    pricing: str | None = None
    pricing_verified: bool = False
    features: list[str] = Field(default_factory=list)
    geography: str | None = None
    business_model: str | None = None
    strengths: list[str]
    weaknesses: list[str]
    positioning: str
    source_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    source: str | None = None


class CompetitorResearchOutput(BaseModel):
    data_available: bool
    research_status: Literal["live", "no_results", "unavailable"]
    competitors: list[Competitor]
    differentiation_opportunity: str
    analysis_basis: str
    limitations: list[str]
    queries: list[str]
    provider: str | None = None
    retrieved_at: str | None = None
    sources: list[dict]
    note: str


class CompetitorResearchTool(BaseTool):
    name = "competitor_research"
    description = (
        "Live, evidence-based competitor research: searches the web for real competitors, checks "
        "their official websites, and returns each competitor's product, pricing, features, target "
        "customers and availability ONLY where a retrieved source supports it (otherwise marked "
        "'Not verified from available sources'), with source URLs. Use when the user asks about "
        "competitors, competition, or alternatives."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = CompetitorResearchInput
    output_model = CompetitorResearchOutput

    def __init__(
        self,
        model: ModelProvider,
        research: ResearchProvider,
        *,
        max_results: int = 5,
        max_sources: int = 6,
        max_fetched_pages: int = 3,
        prompt_chars_per_source: int = 900,
    ):
        self.model = model
        self.research = research
        self.max_results = max_results
        self.max_sources = max_sources
        self.max_fetched_pages = max_fetched_pages
        self.prompt_chars_per_source = prompt_chars_per_source

    def model_view(self, result: dict[str, Any]) -> dict[str, Any]:
        return compact_research_result(result)

    async def execute(self, payload: CompetitorResearchInput, context: ToolContext) -> dict[str, Any]:
        geography = payload.geography or "India"
        queries = build_queries(payload, geography)
        evidence = await gather_evidence(
            self.research, queries, max_results=self.max_results, max_sources=self.max_sources
        )
        if evidence.status != "live":
            headline = UNAVAILABLE_NOTE if evidence.status == "unavailable" else INSUFFICIENT_EVIDENCE
            return _empty(evidence, headline)
        await self._enrich_top_sources(evidence)

        user_prompt = (
            f"Industry: {payload.industry}\n"
            f"Our solution: {payload.solution or 'unspecified'}\n"
            f"Our target customer: {payload.target_customer or 'unspecified'}\n"
            f"Geography: {geography}\n"
            f"Competitors the founder mentioned: {', '.join(payload.known_competitors) or 'none'}\n"
            f"Today's date: {datetime.now(timezone.utc).date().isoformat()}\n\n"
            f"SOURCES:\n{evidence.prompt_block(max_chars_per_source=self.prompt_chars_per_source)}\n"
        )
        parsed, model_error = await safe_generate_json(
            self.model, system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, max_tokens=1400
        )
        if parsed is None:
            reason = model_error or "the AI analysis could not be parsed"
            result = _empty(evidence, f"Sources were retrieved, but {reason.rstrip('.')}.")
            result.update(
                research_status="live",
                provider=", ".join(evidence.providers),
                retrieved_at=evidence.retrieved_at,
                sources=evidence.to_dicts(),
                note="Live sources retrieved; AI analysis unavailable. Open the sources to read the evidence.",
            )
            return result

        competitors, limitations = _validate_competitors(parsed.get("competitors"), evidence)
        limitations += await self._verify_official_sites(competitors, evidence)
        for competitor in competitors:
            _verify_pricing(competitor, evidence)
            competitor["source_urls"] = [s.url for s in (evidence.get(i) for i in competitor["source_ids"]) if s]
            competitor["source"] = competitor["website"] or (competitor["source_urls"] or [None])[0]

        limitations = as_str_list(parsed.get("limitations")) + limitations
        if not competitors:
            limitations.insert(0, "No competitors could be verified from the retrieved sources.")
        age = describe_age(evidence.retrieved_at)
        return {
            "data_available": bool(competitors),
            "research_status": "live",
            "competitors": competitors,
            "differentiation_opportunity": str(
                parsed.get("differentiation_opportunity")
                or "Not enough evidence to identify a clear differentiation angle."
            ),
            "analysis_basis": "Strengths, weaknesses, positioning and differentiation are AI "
            "interpretation of the retrieved sources — not facts stated by them.",
            "limitations": limitations,
            "queries": evidence.queries,
            "provider": ", ".join(evidence.providers),
            "retrieved_at": evidence.retrieved_at,
            "sources": evidence.to_dicts(),
            "note": (
                f"Evidence-based: {len(competitors)} competitor(s) found in {len(evidence.sources)} live source(s). {age}"
                if competitors
                else f"Live sources were retrieved, but no competitors could be verified from them. {age}"
            ).strip(),
        }

    async def _enrich_top_sources(self, evidence: EvidenceSet, count: int = 2) -> None:
        """Search snippets are short; competitor names usually sit in the full page (e.g. a
        'top startups' list). Read the top few result pages so the analysis sees them."""
        targets = [s for s in evidence.sources if not s.content][: min(count, self.max_fetched_pages)]
        pages = await asyncio.gather(*(self.research.fetch(s.url) for s in targets), return_exceptions=True)
        for source, page in zip(targets, pages):
            if isinstance(page, Source) and page.content:
                source.content = page.content
                source.source_date = source.source_date or page.source_date

    async def _verify_official_sites(self, competitors: list[dict], evidence: EvidenceSet) -> list[str]:
        """Fetch claimed official websites; keep a website only if the live page mentions the company."""
        candidates = [c for c in competitors if c.get("website")][: self.max_fetched_pages]
        pages = await asyncio.gather(
            *(self.research.fetch(c["website"]) for c in candidates), return_exceptions=True
        )
        unverified = 0
        for competitor, page in zip(candidates, pages):
            if isinstance(page, Source) and _mentions(competitor["name"], page.text):
                page_id = evidence.add(page)
                if page_id not in competitor["source_ids"]:
                    competitor["source_ids"].append(page_id)
                competitor["website"] = page.url
                competitor["website_verified"] = True
            else:
                unverified += 1
        for competitor in competitors:
            if not competitor["website_verified"]:
                # A website that was neither fetched nor found in the sources is not shown.
                website = competitor.get("website")
                in_sources = website and any(domain_of(s.url) == domain_of(website) for s in evidence.sources)
                if not in_sources:
                    competitor["website"] = None
        return [f"{unverified} official website(s) could not be fetched and verified."] if unverified else []


def build_queries(payload: CompetitorResearchInput, geography: str) -> list[str]:
    queries: list[str] = []
    if payload.known_competitors:
        queries.append(" vs ".join(payload.known_competitors[:3]) + f" {payload.industry}")
    if payload.solution:
        queries.append(f"{payload.solution} competitors alternatives {geography}")
    queries.append(f"top {payload.industry} companies startups {geography}")
    queries.append(f"{payload.industry} software pricing plans {geography}")
    return queries[:3]


def _mentions(name: str, text: str) -> bool:
    text = text.lower()
    if name.lower() in text:
        return True
    tokens = [t for t in _NAME_TOKEN_RE.findall(name.lower()) if len(t) >= 3 and t not in _GENERIC_NAME_WORDS]
    return bool(tokens) and tokens[0] in text


def _validate_competitors(raw: Any, evidence: EvidenceSet) -> tuple[list[dict], list[str]]:
    competitors: list[dict] = []
    dropped = 0
    seen: set[str] = set()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or not str(item.get("name") or "").strip():
            continue
        name = str(item["name"]).strip()
        if name.lower() in seen:
            continue
        ids = evidence.valid_ids(item.get("source_ids") or item.get("sources"))
        # The company itself must be named in a cited source (or, failing that, any source).
        if not any(_mentions(name, t) for t in evidence.texts(ids)):
            ids = [sid for sid in evidence.ids if _mentions(name, evidence.get(sid).text)][:2]
        if not ids:
            dropped += 1
            continue
        seen.add(name.lower())
        texts = evidence.texts(ids)

        features = [
            f
            for f in as_str_list(item.get("features"))
            if numbers_supported(f, texts) and words_supported(f, texts)
        ]
        website = str(item.get("website") or "").strip() or None
        if website and not website.startswith("http"):
            website = f"https://{website}"
        if website and not is_safe_public_url(website):
            website = None

        competitors.append(
            {
                "name": name,
                "website": website,
                "website_verified": False,
                "product": _verified_text(item.get("product"), texts),
                "target_audience": _verified_text(item.get("target_audience"), texts),
                "pricing": str(item.get("pricing")).strip() if item.get("pricing") else None,
                "pricing_verified": False,
                "features": features,
                "geography": _verified_text(item.get("geography"), texts, default=None),
                "business_model": _verified_text(item.get("business_model"), texts, default=None),
                "strengths": as_str_list(item.get("strengths")),
                "weaknesses": as_str_list(item.get("weaknesses")),
                "positioning": str(item.get("positioning") or ""),
                "source_ids": ids,
                "source_urls": [],
                "source": None,
            }
        )
    limitations = (
        [f"{dropped} suggested competitor(s) were discarded because no retrieved source mentions them."]
        if dropped
        else []
    )
    return competitors, limitations


def _verified_text(value: Any, texts: list[str], *, default: str | None = NOT_VERIFIED) -> str | None:
    text = str(value or "").strip()
    if not text or text.lower() in ("null", "none", "unknown", "n/a"):
        return default
    return text if numbers_supported(text, texts) else default


def _verify_pricing(competitor: dict, evidence: EvidenceSet) -> None:
    pricing = competitor.get("pricing")
    texts = evidence.texts(competitor["source_ids"])
    verified = False
    if pricing:
        lowered = pricing.lower()
        if any(ch.isdigit() for ch in pricing):
            verified = numbers_supported(pricing, texts)
        else:
            combined = " ".join(texts).lower()
            verified = any(word in lowered and word in combined for word in _PRICING_WORDS)
    competitor["pricing_verified"] = verified
    if not verified:
        competitor["pricing"] = NOT_VERIFIED


def _empty(evidence: EvidenceSet, headline: str) -> dict[str, Any]:
    return {
        "data_available": False,
        "research_status": evidence.status,
        "competitors": [],
        "differentiation_opportunity": headline,
        "analysis_basis": "No analysis was produced because no usable evidence was analysed.",
        "limitations": [headline],
        "queries": evidence.queries,
        "provider": None,
        "retrieved_at": None,
        "sources": [],
        "note": headline,
    }
