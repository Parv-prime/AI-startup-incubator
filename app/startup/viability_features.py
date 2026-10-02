"""Deterministic feature extraction for the viability model.

A 3B tool-calling model reliably omits optional numeric arguments rather than
reasoning about each one, so factor scores are derived here from whatever
analyses have actually been gathered for the startup instead of trusting the
LLM to invent 8 numbers. Any factor the LLM does pass explicitly still wins
(see viability_predictor.py) — this is only the fallback.
"""

from __future__ import annotations

from typing import Any

DEFAULT = 50.0


def derive_features(
    *,
    profile: Any,
    market: dict | None,
    competitor: dict | None,
    financial: dict | None,
) -> dict[str, float]:
    return {
        "market_demand": _market_demand(market),
        "competition": _competition(competitor),
        "problem_severity": _problem_severity(profile, market),
        "customer_accessibility": _customer_accessibility(profile),
        "business_model_strength": _business_model_strength(profile, financial),
        "startup_cost": _startup_cost(financial),
        "scalability": _scalability(profile),
        "growth_potential": _growth_potential(market),
    }


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _market_demand(market: dict | None) -> float:
    if not market:
        return DEFAULT
    score = DEFAULT
    score += 8 * min(len(market.get("opportunities") or []), 3)
    score += 5 * min(len(market.get("trends") or []), 3)
    score -= 5 * min(len(market.get("risks") or []), 3)
    return _clamp(score)


def _competition(competitor: dict | None) -> float:
    if not competitor:
        return DEFAULT
    count = len(competitor.get("competitors") or [])
    if count == 0:
        return _clamp(DEFAULT - 15)  # few known competitors -> less competitive pressure
    if count <= 2:
        return _clamp(DEFAULT)
    return _clamp(DEFAULT + 10 * min(count - 2, 3))


def _problem_severity(profile: Any, market: dict | None) -> float:
    score = DEFAULT
    if profile.problem:
        score += 5
    if market and market.get("risks"):
        score += 5
    return _clamp(score)


def _customer_accessibility(profile: Any) -> float:
    score = DEFAULT
    if profile.target_customer:
        score += 12
    if profile.geography:
        score += 8
    return _clamp(score)


def _business_model_strength(profile: Any, financial: dict | None) -> float:
    if financial and financial.get("gross_margin_pct") is not None:
        # Map 0-100% margin onto a 20-90 score band.
        margin = financial["gross_margin_pct"]
        return _clamp(20 + margin * 0.7)
    score = DEFAULT
    if profile.business_model:
        score += 8
    return _clamp(score)


def _startup_cost(financial: dict | None) -> float:
    """Affordability score: lower real-world cost -> higher score."""
    if not financial:
        return DEFAULT
    monthly_cost = financial.get("monthly_operating_cost")
    if monthly_cost is None:
        return DEFAULT
    if monthly_cost <= 1000:
        return 85.0
    if monthly_cost <= 5000:
        return 65.0
    if monthly_cost <= 20000:
        return 45.0
    return 25.0


def _scalability(profile: Any) -> float:
    score = DEFAULT
    model = (profile.business_model or "").lower()
    if any(word in model for word in ("saas", "subscription", "platform", "marketplace", "app")):
        score += 15
    return _clamp(score)


def _growth_potential(market: dict | None) -> float:
    if not market:
        return DEFAULT
    score = DEFAULT
    score += 7 * min(len(market.get("trends") or []), 3)
    score += 5 * min(len(market.get("opportunities") or []), 3)
    return _clamp(score)
