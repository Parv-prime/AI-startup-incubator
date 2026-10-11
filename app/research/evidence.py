"""Evidence layer between raw search results and the LLM.

Collects sources for a set of queries, numbers them [S1], [S2], ... for the
prompt, and provides deterministic guards the research tools apply to the
LLM's output: citations must reference retrieved sources, and numbers in a
"source-backed" claim must actually appear in the cited source text.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from app.core.logging import get_logger
from app.research.base import (
    UNAVAILABLE_MESSAGE,
    ResearchProvider,
    ResearchUnavailableError,
    Source,
    Topic,
    clip,
    domain_of,
)

logger = get_logger(__name__)

NOT_VERIFIED = "Not verified from available sources"
INSUFFICIENT_EVIDENCE = "Insufficient reliable evidence was retrieved to verify this claim."
UNAVAILABLE_NOTE = (
    f"{UNAVAILABLE_MESSAGE} The following information should not be treated as current market research."
)

EvidenceStatus = Literal["live", "no_results", "unavailable"]

_GOV_SUFFIXES = (".gov", ".gov.in", ".nic.in", ".gov.uk", ".gov.au", ".gc.ca", ".europa.eu", ".gob", ".go.jp")
_GOV_DOMAINS = {"rbi.org.in", "sebi.gov.in", "fssai.gov.in", "data.gov.in", "who.int", "un.org", "oecd.org"}
_ACADEMIC_SUFFIXES = (".edu", ".ac.in", ".ac.uk", ".edu.au")
_ACADEMIC_DOMAINS = {"arxiv.org", "ncbi.nlm.nih.gov", "nature.com", "sciencedirect.com", "springer.com", "jstor.org"}
_RESEARCH_ORG_DOMAINS = {
    "worldbank.org", "imf.org", "weforum.org", "mckinsey.com", "bain.com", "bcg.com", "deloitte.com",
    "pwc.com", "kpmg.com", "ey.com", "nasscom.in", "ibef.org", "statista.com", "gartner.com", "idc.com",
}
_NEWS_DOMAINS = {
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "bbc.com", "bbc.co.uk", "cnbc.com", "forbes.com",
    "techcrunch.com", "theguardian.com", "nytimes.com", "economictimes.indiatimes.com", "livemint.com",
    "business-standard.com", "thehindu.com", "thehindubusinessline.com", "hindustantimes.com",
    "moneycontrol.com", "ndtv.com", "indianexpress.com", "financialexpress.com", "inc42.com",
    "yourstory.com", "entrackr.com", "the-ken.com",
}
_KIND_RANK = {"government": 0, "academic": 1, "research": 2, "news": 3, "web": 4}

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def source_kind(url: str) -> str:
    domain = domain_of(url)
    if domain in _GOV_DOMAINS or domain.endswith(_GOV_SUFFIXES):
        return "government"
    if domain in _ACADEMIC_DOMAINS or domain.endswith(_ACADEMIC_SUFFIXES):
        return "academic"
    if domain in _RESEARCH_ORG_DOMAINS or any(domain.endswith("." + d) for d in _RESEARCH_ORG_DOMAINS):
        return "research"
    if domain in _NEWS_DOMAINS or any(domain.endswith("." + d) for d in _NEWS_DOMAINS):
        return "news"
    return "web"


def describe_age(retrieved_at: str | None, *, now: datetime | None = None) -> str:
    if not retrieved_at:
        return ""
    try:
        then = datetime.fromisoformat(retrieved_at)
    except ValueError:
        return ""
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    minutes = int(((now or datetime.now(timezone.utc)) - then).total_seconds() // 60)
    if minutes < 2:
        return "Retrieved just now."
    if minutes < 90:
        return f"Retrieved approximately {minutes} minutes ago."
    hours = round(minutes / 60)
    if hours < 48:
        return f"Retrieved approximately {hours} hours ago."
    return f"Retrieved approximately {round(hours / 24)} days ago."


def _numbers(text: str) -> set[str]:
    found = set()
    for raw in _NUMBER_RE.findall(text or ""):
        value = raw.replace(",", "").rstrip(".")
        # Single digits ("3 segments", "top 5") are too common to be meaningful evidence.
        if len(value.replace(".", "")) >= 2:
            found.add(value)
    return found


def numbers_supported(claim: str, source_texts: list[str]) -> bool:
    """True when every multi-digit number in `claim` appears in the cited source text."""
    wanted = _numbers(claim)
    if not wanted:
        return True
    available: set[str] = set()
    for text in source_texts:
        available |= _numbers(text)
    return wanted <= available


_WORD_RE = re.compile(r"[a-z0-9]{4,}")


def words_supported(phrase: str, source_texts: list[str], *, threshold: float = 0.5) -> bool:
    """True when at least `threshold` of the phrase's significant words occur in the sources —
    a cheap guard against features/claims with no basis in the retrieved text."""
    words = set(_WORD_RE.findall(phrase.lower()))
    if not words:
        return True
    available = set(_WORD_RE.findall(" ".join(source_texts).lower()))
    return len(words & available) / len(words) >= threshold


@dataclass
class EvidenceSet:
    queries: list[str]
    sources: list[Source] = field(default_factory=list)
    status: EvidenceStatus = "no_results"

    @property
    def ids(self) -> list[str]:
        return [f"S{i}" for i in range(1, len(self.sources) + 1)]

    def get(self, source_id: str) -> Source | None:
        try:
            index = int(str(source_id).strip().strip("[]").upper().lstrip("S")) - 1
        except ValueError:
            return None
        return self.sources[index] if 0 <= index < len(self.sources) else None

    def valid_ids(self, raw: Any) -> list[str]:
        """Keep only citations that point at a retrieved source, normalized to 'S<n>'."""
        items = raw if isinstance(raw, list) else [raw] if raw else []
        out: list[str] = []
        for item in items:
            source = self.get(str(item))
            if source is not None:
                sid = f"S{self.sources.index(source) + 1}"
                if sid not in out:
                    out.append(sid)
        return out

    def texts(self, source_ids: list[str]) -> list[str]:
        return [s.text for s in (self.get(i) for i in source_ids) if s is not None]

    def find_by_url(self, url: str) -> str | None:
        for i, source in enumerate(self.sources, start=1):
            if source.url == url:
                return f"S{i}"
        return None

    def add(self, source: Source) -> str:
        existing = self.find_by_url(source.url)
        if existing:
            return existing
        self.sources.append(source)
        if self.status != "live":
            self.status = "live"
        return f"S{len(self.sources)}"

    @property
    def retrieved_at(self) -> str | None:
        stamps = sorted(s.retrieved_at for s in self.sources if s.retrieved_at)
        return stamps[0] if stamps else None

    @property
    def providers(self) -> list[str]:
        seen: list[str] = []
        for s in self.sources:
            if s.provider not in seen:
                seen.append(s.provider)
        return seen

    def prompt_block(self, *, max_chars_per_source: int = 1200) -> str:
        if not self.sources:
            return "(no sources were retrieved)"
        blocks = []
        for sid, s in zip(self.ids, self.sources):
            body = s.content or s.snippet
            blocks.append(
                f"[{sid}] {s.title}\n"
                f"URL: {s.url}\n"
                f"Published: {s.source_date or 'Not available'} | Type: {source_kind(s.url)}\n"
                f"Excerpt: {clip(body, max_chars_per_source)}"
            )
        return "\n\n".join(blocks)

    def to_dicts(self) -> list[dict[str, Any]]:
        return [
            {
                "id": sid,
                "title": s.title,
                "url": s.url,
                "domain": s.domain,
                "snippet": clip(s.snippet or s.content, 300),
                "source_date": s.source_date,
                "retrieved_at": s.retrieved_at,
                "provider": s.provider,
                "source_type": "web_search",
                "source_kind": source_kind(s.url),
            }
            for sid, s in zip(self.ids, self.sources)
        ]


def compact_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Source list trimmed for the LLM: enough to cite (id, title, URL, date), no excerpts."""
    return [
        {key: s.get(key) for key in ("id", "title", "url", "source_date")}
        for s in sources
        if isinstance(s, dict)
    ]


def compact_research_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("research_status") in ("unavailable", "no_results"):
        # Nothing was retrieved: one clear statement. (Repeating the same sentence across
        # several fields makes small models loop on it.)
        return {
            "research_status": result["research_status"],
            "data_available": False,
            "note": result.get("note"),
            "instruction": "Tell the user this plainly in one sentence. Do not invent figures, "
            "sources or competitors to fill the gap.",
        }
    view = {k: v for k, v in result.items() if k not in ("queries", "provider")}
    view["sources"] = compact_sources(result.get("sources") or [])
    if isinstance(result.get("key_findings"), list):
        view["key_findings"] = [
            {"claim": f.get("claim"), "type": f.get("type"), "source_ids": f.get("source_ids")}
            for f in result["key_findings"]
            if isinstance(f, dict)
        ]
    return view


async def gather_evidence(
    provider: ResearchProvider,
    queries: list[str],
    *,
    max_results: int,
    max_sources: int,
    recency_days: int | None = None,
    topic: Topic | None = None,
) -> EvidenceSet:
    """Run the queries concurrently, dedupe by URL, rank authoritative sources first."""
    evidence = EvidenceSet(queries=queries)
    outcomes = await asyncio.gather(
        *(provider.search(q, max_results, recency_days, topic=topic) for q in queries),
        return_exceptions=True,
    )

    collected: list[Source] = []
    unavailable = 0
    for query, outcome in zip(queries, outcomes):
        if isinstance(outcome, ResearchUnavailableError):
            unavailable += 1
            continue
        if isinstance(outcome, BaseException):
            logger.warning("research_query_failed", extra={"query": query, "error": type(outcome).__name__})
            unavailable += 1
            continue
        collected.extend(outcome)

    seen: set[str] = set()
    unique: list[Source] = []
    for source in collected:
        key = source.url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            unique.append(source)
    # Stable sort: authoritative kinds first, provider relevance order preserved within a kind.
    unique.sort(key=lambda s: _KIND_RANK.get(source_kind(s.url), 9))
    evidence.sources = unique[:max_sources]

    if evidence.sources:
        evidence.status = "live"
    elif queries and unavailable == len(queries):
        evidence.status = "unavailable"
    else:
        evidence.status = "no_results"
    return evidence
