from __future__ import annotations

from typing import Any

from app.agent.types import AgentResult, ToolEvent
from app.database.models import Project

_LABELS = {
    "market_research": "Researching market",
    "competitor_research": "Analyzing competitors",
    "financial_analysis": "Calculating financials",
    "startup_viability_predictor": "Evaluating viability",
    "memory_write": "Saving project context",
    "memory_search": "Recalling project context",
    "calculator": "Calculating",
}


def build_response(*, result: AgentResult, project: Project) -> dict[str, Any]:
    tool_activity = [_to_activity(event) for event in result.tool_events]

    market = _find_result(result.tool_events, "market_research")
    competitor = _find_result(result.tool_events, "competitor_research")
    financial = _find_result(result.tool_events, "financial_analysis")
    viability = _find_result(result.tool_events, "startup_viability_predictor")

    analysis = None
    if market or competitor or financial:
        analysis = {
            "market_research": market,
            "competitor_research": competitor,
            "financial_analysis": financial,
        }

    recommendations = _build_recommendations(financial, viability)
    sources = _collect_sources(market, competitor)

    errors = [event.error for event in result.tool_events if event.status == "error" and event.error]
    if result.status == "failed" and result.output:
        errors.append(result.output)

    return {
        "success": result.status == "completed",
        "response": result.output,
        "project_id": project.id,
        "tool_activity": tool_activity,
        "analysis": analysis,
        "viability": viability,
        "recommendations": recommendations,
        "sources": sources,
        "errors": errors,
    }


def _to_activity(event: ToolEvent) -> dict:
    label = _LABELS.get(event.name, event.name.replace("_", " ").title())
    if event.status == "ok":
        message = f"{label} completed"
        status = "completed"
    else:
        message = f"{label} failed: {event.error}"
        status = "failed"
    return {
        "tool_name": event.name,
        "status": status,
        "message": message,
        "duration_ms": int(event.duration_ms) if event.duration_ms is not None else None,
    }


def _find_result(events: list[ToolEvent], name: str) -> dict | None:
    for event in reversed(events):
        if event.name == name and event.status == "ok" and event.result:
            return event.result
    return None


def _build_recommendations(financial: dict | None, viability: dict | None) -> list[dict]:
    recs: list[dict] = []
    if financial and financial.get("monthly_profit_loss") is not None:
        if financial["monthly_profit_loss"] < 0:
            recs.append(
                {
                    "title": "Close the monthly cash gap",
                    "description": (
                        f"Projected monthly loss of {abs(financial['monthly_profit_loss']):.2f}. "
                        "Reduce operating cost, raise price, or grow toward the break-even point."
                    ),
                    "priority": "High",
                    "category": "Finance",
                }
            )
    if viability and viability.get("factors"):
        weakest = min(viability["factors"].items(), key=lambda kv: kv[1], default=None)
        if weakest and weakest[1] < 50:
            recs.append(
                {
                    "title": f"Strengthen {weakest[0].replace('_', ' ')}",
                    "description": f"Scored {weakest[1]:.0f}/100 — the weakest input to the viability score.",
                    "priority": "Medium",
                    "category": "Viability",
                }
            )
    return recs


def _collect_sources(market: dict | None, competitor: dict | None) -> list[dict]:
    sources: list[dict] = []
    for block in (market, competitor):
        if not block:
            continue
        for raw in block.get("sources") or []:
            if isinstance(raw, dict) and raw.get("title"):
                sources.append(
                    {
                        "title": raw["title"],
                        "url": raw.get("url"),
                        "source_type": raw.get("source_type", "unknown"),
                    }
                )
    return sources
