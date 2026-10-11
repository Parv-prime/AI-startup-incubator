"""Shared helpers for turning retrieved evidence + LLM output into cited findings."""

from __future__ import annotations

import re
from typing import Any

from app.core.errors import AgentError
from app.core.logging import get_logger
from app.models.base import ModelProvider
from app.models.structured import generate_json
from app.research.evidence import EvidenceSet, numbers_supported

logger = get_logger(__name__)

GROUNDING_RULES = """STRICT EVIDENCE RULES — follow all of them:
- Use ONLY the numbered sources [S1], [S2], ... below for factual claims about current external
  information (companies, prices, market sizes, growth rates, dates, regulations, news).
- Every factual claim must list the id(s) of the source(s) that directly support it.
- Do NOT invent statistics, market sizes, growth rates, prices, companies, dates, regulations,
  citations or URLs. Never cite a source id that is not listed. Never write a URL.
- Never claim a source says something it does not say. If sources disagree, say so.
- Clearly separate source-backed facts from your own interpretation. Mark a claim "derived" only
  if it is a calculation or direct inference from the cited sources.
- Note when a source looks old (check its Published date) or is not authoritative.
- If the evidence is insufficient for something, say "Insufficient reliable evidence was retrieved"
  in limitations instead of filling the gap."""

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[a-z0-9]+")


async def safe_generate_json(model: ModelProvider, **kwargs: Any) -> tuple[dict[str, Any] | None, str | None]:
    """generate_json that reports (instead of raising) model/provider failures, so a research
    tool can still return the evidence it retrieved when the LLM is down."""
    try:
        return await generate_json(model, **kwargs), None
    except AgentError as exc:
        logger.warning("research_synthesis_model_error", extra={"error": exc.code})
        return None, exc.message


def best_excerpt(claim: str, text: str, limit: int = 240) -> str:
    """The sentence of `text` that shares the most words with `claim` — a short real
    excerpt from the source, not an LLM paraphrase."""
    claim_words = set(_WORD_RE.findall(claim.lower()))
    best, best_score = "", -1
    for sentence in _SENTENCE_SPLIT.split(" ".join((text or "").split())):
        score = len(claim_words & set(_WORD_RE.findall(sentence.lower())))
        if score > best_score:
            best, best_score = sentence, score
    best = best.strip()
    return best if len(best) <= limit else best[: limit - 1].rstrip() + "…"


def validate_findings(raw: Any, evidence: EvidenceSet) -> tuple[list[dict[str, Any]], list[str]]:
    """Keep only findings that cite retrieved sources and whose numbers appear in them."""
    findings: list[dict[str, Any]] = []
    uncited = unsupported = 0
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        if not claim:
            continue
        ids = evidence.valid_ids(item.get("source_ids") or item.get("sources") or item.get("source_id"))
        if not ids:
            uncited += 1
            continue
        kind = "derived" if str(item.get("type") or "").lower() == "derived" else "evidence"
        texts = evidence.texts(ids)
        if kind == "evidence" and not numbers_supported(claim, texts):
            unsupported += 1
            continue
        first = evidence.get(ids[0])
        findings.append(
            {
                "claim": claim,
                "type": kind,
                "evidence": best_excerpt(claim, first.text) if first else "",
                "source_ids": ids,
                "source_title": first.title if first else None,
                "source_url": first.url if first else None,
                "source_date": first.source_date if first else None,
            }
        )

    limitations: list[str] = []
    if uncited:
        limitations.append(f"{uncited} model-generated claim(s) were discarded because they cited no retrieved source.")
    if unsupported:
        limitations.append(
            f"{unsupported} claim(s) were discarded because their figures did not appear in the cited source."
        )
    return findings, limitations


def filter_unsupported_numbers(items: list[str], evidence: EvidenceSet) -> tuple[list[str], int]:
    """Drop interpretation bullets that slip in figures found in none of the sources."""
    all_text = [s.text for s in evidence.sources]
    kept = [item for item in items if numbers_supported(item, all_text)]
    return kept, len(items) - len(kept)


def as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
