from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Competitor,
    FinancialAnalysis,
    MarketResearch,
    Recommendation,
    RoadmapItem,
    StartupReport,
    ViabilityAssessment,
)


# ------------------------------------------------------------- market research --

async def save_market_research(session: AsyncSession, *, project_id: str, data: dict) -> MarketResearch:
    row = MarketResearch(project_id=project_id, data=data)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def latest_market_research(session: AsyncSession, *, project_id: str) -> MarketResearch | None:
    stmt = (
        select(MarketResearch)
        .where(MarketResearch.project_id == project_id)
        .order_by(MarketResearch.created_at.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def list_market_research(session: AsyncSession, *, project_id: str) -> list[MarketResearch]:
    stmt = (
        select(MarketResearch)
        .where(MarketResearch.project_id == project_id)
        .order_by(MarketResearch.created_at.desc())
    )
    return list((await session.scalars(stmt)).all())


# ---------------------------------------------------------------- competitors --

async def add_competitor(session: AsyncSession, *, project_id: str, fields: dict) -> Competitor:
    row = Competitor(
        project_id=project_id,
        name=fields.get("name") or "Unnamed competitor",
        description=fields.get("description"),
        product=fields.get("product"),
        pricing=fields.get("pricing"),
        strengths=fields.get("strengths") or [],
        weaknesses=fields.get("weaknesses") or [],
        target_market=fields.get("target_market"),
        differentiation=fields.get("differentiation"),
        source=fields.get("source"),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_competitors(session: AsyncSession, *, project_id: str) -> list[Competitor]:
    stmt = (
        select(Competitor).where(Competitor.project_id == project_id).order_by(Competitor.created_at.desc())
    )
    return list((await session.scalars(stmt)).all())


async def replace_competitors_from_research(
    session: AsyncSession, *, project_id: str, competitors: list[dict]
) -> list[Competitor]:
    """Store structured competitor rows synthesized by the competitor_research tool."""
    created = []
    for item in competitors:
        row = Competitor(
            project_id=project_id,
            name=str(item.get("name") or "Unnamed competitor"),
            description=item.get("description") or item.get("positioning"),
            product=item.get("product"),
            pricing=item.get("pricing"),
            strengths=item.get("strengths") or [],
            weaknesses=item.get("weaknesses") or [],
            target_market=item.get("target_market") or item.get("target_audience"),
            differentiation=item.get("differentiation") or item.get("positioning"),
            source=item.get("source") or "AI-synthesized (non-live)",
        )
        session.add(row)
        created.append(row)
    await session.commit()
    for row in created:
        await session.refresh(row)
    return created


# ----------------------------------------------------------- financial analysis --

async def save_financial_analysis(session: AsyncSession, *, project_id: str, data: dict) -> FinancialAnalysis:
    row = FinancialAnalysis(project_id=project_id, data=data)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def latest_financial_analysis(session: AsyncSession, *, project_id: str) -> FinancialAnalysis | None:
    stmt = (
        select(FinancialAnalysis)
        .where(FinancialAnalysis.project_id == project_id)
        .order_by(FinancialAnalysis.created_at.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def list_financial_analysis(session: AsyncSession, *, project_id: str) -> list[FinancialAnalysis]:
    stmt = (
        select(FinancialAnalysis)
        .where(FinancialAnalysis.project_id == project_id)
        .order_by(FinancialAnalysis.created_at.desc())
    )
    return list((await session.scalars(stmt)).all())


# --------------------------------------------------------------------- viability --

async def save_viability(session: AsyncSession, *, project_id: str, data: dict) -> ViabilityAssessment:
    row = ViabilityAssessment(
        project_id=project_id,
        score=data["score"],
        classification=data["classification"],
        factors=data["factors"],
        feature_importance=data["feature_importance"],
        model_version=data["model_version"],
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def latest_viability(session: AsyncSession, *, project_id: str) -> ViabilityAssessment | None:
    stmt = (
        select(ViabilityAssessment)
        .where(ViabilityAssessment.project_id == project_id)
        .order_by(ViabilityAssessment.created_at.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


# ---------------------------------------------------------------------- roadmap --

async def add_roadmap_item(session: AsyncSession, *, project_id: str, fields: dict) -> RoadmapItem:
    row = RoadmapItem(
        project_id=project_id,
        phase=fields.get("phase"),
        title=fields.get("title") or "Untitled milestone",
        description=fields.get("description"),
        priority=fields.get("priority") or "Medium",
        status=fields.get("status") or "Pending",
        target_date=fields.get("target_date"),
        dependencies=fields.get("dependencies") or [],
        notes=fields.get("notes"),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_roadmap_items(session: AsyncSession, *, project_id: str) -> list[RoadmapItem]:
    stmt = (
        select(RoadmapItem).where(RoadmapItem.project_id == project_id).order_by(RoadmapItem.created_at)
    )
    return list((await session.scalars(stmt)).all())


async def get_owned_roadmap_item(session: AsyncSession, *, item_id: str, project_id: str) -> RoadmapItem | None:
    row = await session.get(RoadmapItem, item_id)
    if row is None or row.project_id != project_id:
        return None
    return row


async def update_roadmap_item(session: AsyncSession, *, item: RoadmapItem, fields: dict) -> RoadmapItem:
    for key in ("phase", "title", "description", "priority", "status", "target_date", "notes"):
        if fields.get(key) is not None:
            setattr(item, key, fields[key])
    if fields.get("dependencies") is not None:
        item.dependencies = fields["dependencies"]
    item.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(item)
    return item


async def delete_roadmap_item(session: AsyncSession, *, item: RoadmapItem) -> None:
    await session.delete(item)
    await session.commit()


# --------------------------------------------------------------- recommendations --

async def add_recommendation(session: AsyncSession, *, project_id: str, fields: dict) -> Recommendation:
    row = Recommendation(
        project_id=project_id,
        title=fields.get("title") or "Recommendation",
        description=fields.get("description") or "",
        priority=fields.get("priority") or "Medium",
        category=fields.get("category") or "General",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_recommendations(session: AsyncSession, *, project_id: str, limit: int = 20) -> list[Recommendation]:
    stmt = (
        select(Recommendation)
        .where(Recommendation.project_id == project_id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


# --------------------------------------------------------------------- reports --

async def save_report(session: AsyncSession, *, project_id: str, content: dict) -> StartupReport:
    row = StartupReport(project_id=project_id, content=content)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_reports(session: AsyncSession, *, project_id: str) -> list[StartupReport]:
    stmt = (
        select(StartupReport)
        .where(StartupReport.project_id == project_id)
        .order_by(StartupReport.generated_at.desc())
    )
    return list((await session.scalars(stmt)).all())


async def latest_report(session: AsyncSession, *, project_id: str) -> StartupReport | None:
    stmt = (
        select(StartupReport)
        .where(StartupReport.project_id == project_id)
        .order_by(StartupReport.generated_at.desc())
        .limit(1)
    )
    return await session.scalar(stmt)
