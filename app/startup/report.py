from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Project
from app.projects import analyses_store


async def build_report(session: AsyncSession, project: Project) -> dict:
    market_row = await analyses_store.latest_market_research(session, project_id=project.id)
    competitors = await analyses_store.list_competitors(session, project_id=project.id)
    financial_row = await analyses_store.latest_financial_analysis(session, project_id=project.id)
    viability_row = await analyses_store.latest_viability(session, project_id=project.id)
    roadmap = await analyses_store.list_roadmap_items(session, project_id=project.id)

    market = market_row.data if market_row else None
    competitor = (
        {
            "competitors": [
                {
                    "name": c.name,
                    "description": c.description,
                    "product": c.product,
                    "pricing": c.pricing,
                    "strengths": c.strengths,
                    "weaknesses": c.weaknesses,
                    "target_market": c.target_market,
                    "differentiation": c.differentiation,
                }
                for c in competitors
            ]
        }
        if competitors
        else None
    )
    financial = financial_row.data if financial_row else None
    viability = (
        {
            "score": viability_row.score,
            "classification": viability_row.classification,
            "factors": viability_row.factors,
            "feature_importance": viability_row.feature_importance,
            "model_version": viability_row.model_version,
        }
        if viability_row
        else None
    )

    profile = _profile_dict(project)
    risks = list((market or {}).get("risks") or [])
    opportunities = list((market or {}).get("opportunities") or [])

    recommendations = _build_recommendations(profile, market, competitor, financial, viability)
    next_steps = _build_next_steps(profile, market, competitor, financial, viability)

    return {
        "profile": profile,
        "executive_summary": _executive_summary(profile, viability),
        "market_analysis": market,
        "competitor_analysis": competitor,
        "financial_analysis": financial,
        "viability": viability,
        "risks": risks,
        "opportunities": opportunities,
        "recommendations": recommendations,
        "next_steps": next_steps,
        "roadmap": [
            {
                "phase": r.phase,
                "title": r.title,
                "status": r.status,
                "priority": r.priority,
            }
            for r in roadmap
        ],
    }


def _profile_dict(project: Project) -> dict:
    return {
        "startup_name": project.name,
        "industry": project.industry,
        "problem": project.problem,
        "solution": project.solution,
        "target_customer": project.target_customer,
        "geography": project.geography,
        "business_model": project.business_model,
        "startup_stage": project.stage,
        "budget": project.budget,
        "goals": project.goals,
    }


def _executive_summary(profile: dict, viability: dict | None) -> str:
    name = profile.get("startup_name") or "This startup"
    industry = f" in {profile['industry']}" if profile.get("industry") else ""
    problem = f" addressing: {profile['problem']}." if profile.get("problem") else "."
    viability_line = ""
    if viability:
        viability_line = (
            f" The viability model estimates a score of {viability['score']}/100 "
            f"({viability['classification']})."
        )
    return f"{name}{industry}{problem}{viability_line}".strip()


def _build_recommendations(
    profile: dict,
    market: dict | None,
    competitor: dict | None,
    financial: dict | None,
    viability: dict | None,
) -> list[dict]:
    recs: list[dict] = []

    if market is None:
        recs.append(
            {
                "title": "Validate market demand",
                "description": "No market research has been run yet. Understanding demand and "
                "target segments should come before deeper investment.",
                "priority": "High",
                "category": "Market",
            }
        )
    if competitor is None:
        recs.append(
            {
                "title": "Map the competitive landscape",
                "description": "No competitor research has been run yet. Knowing who else "
                "serves this problem clarifies differentiation.",
                "priority": "Medium",
                "category": "Competition",
            }
        )
    if financial is None:
        recs.append(
            {
                "title": "Model unit economics",
                "description": "No financial analysis has been run yet. Break-even and runway "
                "numbers are needed before committing budget.",
                "priority": "High",
                "category": "Finance",
            }
        )
    elif financial.get("monthly_profit_loss") is not None and financial["monthly_profit_loss"] < 0:
        recs.append(
            {
                "title": "Close the monthly cash gap",
                "description": f"Current unit economics project a monthly loss of "
                f"{abs(financial['monthly_profit_loss']):.2f}. Reduce operating cost, raise "
                f"price, or grow customers toward the break-even point.",
                "priority": "High",
                "category": "Finance",
            }
        )

    if viability is not None:
        weakest = min(viability["factors"].items(), key=lambda kv: kv[1], default=None)
        if weakest and weakest[1] < 50:
            recs.append(
                {
                    "title": f"Strengthen {weakest[0].replace('_', ' ')}",
                    "description": f"This factor scored {weakest[0].replace('_', ' ')} "
                    f"at {weakest[1]:.0f}/100, the weakest input to the viability score.",
                    "priority": "Medium",
                    "category": "Viability",
                }
            )

    if competitor and competitor.get("differentiation_opportunity"):
        recs.append(
            {
                "title": "Lean into differentiation",
                "description": competitor["differentiation_opportunity"],
                "priority": "Medium",
                "category": "Positioning",
            }
        )

    return recs


def _build_next_steps(
    profile: dict,
    market: dict | None,
    competitor: dict | None,
    financial: dict | None,
    viability: dict | None,
) -> list[str]:
    steps = []
    stage = (profile.get("startup_stage") or "").lower()
    if not stage or stage in {"idea", "concept"}:
        steps.append("Talk to 5-10 target customers to validate the problem before building.")
    if market is None:
        steps.append("Run market research to size demand and identify customer segments.")
    if competitor is None:
        steps.append("Run competitor research to confirm the differentiation angle.")
    if financial is None:
        steps.append("Run financial analysis to determine break-even customers and runway.")
    if viability is None:
        steps.append("Run the viability model once research and financials are gathered.")
    if not steps:
        steps.append("Prepare an MVP scope and validate it with early users.")
    return steps
