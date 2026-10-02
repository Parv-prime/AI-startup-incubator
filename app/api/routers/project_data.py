from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project, get_session
from app.api.schemas_project_data import (
    CompetitorCreateRequest,
    CompetitorResponse,
    FinancialAnalysisResponse,
    MarketResearchResponse,
    RecommendationResponse,
    ReportResponse,
    RoadmapItemCreateRequest,
    RoadmapItemResponse,
    RoadmapItemUpdateRequest,
    ViabilityResponse,
)
from app.database.models import Project
from app.projects import analyses_store
from app.startup.report import build_report

router = APIRouter(prefix="/api/v1/projects/{project_id}", tags=["project-data"])


@router.get("/market-research", response_model=list[MarketResearchResponse])
async def list_market_research(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> list[MarketResearchResponse]:
    rows = await analyses_store.list_market_research(session, project_id=project.id)
    return [MarketResearchResponse.model_validate(r, from_attributes=True) for r in rows]


@router.get("/competitors", response_model=list[CompetitorResponse])
async def list_competitors(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> list[CompetitorResponse]:
    rows = await analyses_store.list_competitors(session, project_id=project.id)
    return [CompetitorResponse.model_validate(r, from_attributes=True) for r in rows]


@router.post("/competitors", response_model=CompetitorResponse, status_code=201)
async def add_competitor(
    payload: CompetitorCreateRequest,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> CompetitorResponse:
    row = await analyses_store.add_competitor(session, project_id=project.id, fields=payload.model_dump())
    return CompetitorResponse.model_validate(row, from_attributes=True)


@router.get("/financial", response_model=list[FinancialAnalysisResponse])
async def list_financial(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> list[FinancialAnalysisResponse]:
    rows = await analyses_store.list_financial_analysis(session, project_id=project.id)
    return [FinancialAnalysisResponse.model_validate(r, from_attributes=True) for r in rows]


@router.get("/viability", response_model=ViabilityResponse | None)
async def get_viability(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> ViabilityResponse | None:
    row = await analyses_store.latest_viability(session, project_id=project.id)
    return ViabilityResponse.model_validate(row, from_attributes=True) if row else None


@router.get("/roadmap", response_model=list[RoadmapItemResponse])
async def list_roadmap(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> list[RoadmapItemResponse]:
    rows = await analyses_store.list_roadmap_items(session, project_id=project.id)
    return [RoadmapItemResponse.model_validate(r, from_attributes=True) for r in rows]


@router.post("/roadmap", response_model=RoadmapItemResponse, status_code=201)
async def create_roadmap_item(
    payload: RoadmapItemCreateRequest,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> RoadmapItemResponse:
    row = await analyses_store.add_roadmap_item(session, project_id=project.id, fields=payload.model_dump())
    return RoadmapItemResponse.model_validate(row, from_attributes=True)


@router.put("/roadmap/{item_id}", response_model=RoadmapItemResponse)
async def update_roadmap_item(
    item_id: str,
    payload: RoadmapItemUpdateRequest,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> RoadmapItemResponse:
    item = await analyses_store.get_owned_roadmap_item(session, item_id=item_id, project_id=project.id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roadmap item not found.")
    item = await analyses_store.update_roadmap_item(session, item=item, fields=payload.model_dump())
    return RoadmapItemResponse.model_validate(item, from_attributes=True)


@router.delete("/roadmap/{item_id}", status_code=204)
async def delete_roadmap_item(
    item_id: str,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> None:
    item = await analyses_store.get_owned_roadmap_item(session, item_id=item_id, project_id=project.id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roadmap item not found.")
    await analyses_store.delete_roadmap_item(session, item=item)


@router.get("/recommendations", response_model=list[RecommendationResponse])
async def list_recommendations(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> list[RecommendationResponse]:
    rows = await analyses_store.list_recommendations(session, project_id=project.id)
    return [RecommendationResponse.model_validate(r, from_attributes=True) for r in rows]


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> list[ReportResponse]:
    rows = await analyses_store.list_reports(session, project_id=project.id)
    return [ReportResponse.model_validate(r, from_attributes=True) for r in rows]


@router.post("/reports", response_model=ReportResponse, status_code=201)
async def generate_report(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    content = await build_report(session, project)
    row = await analyses_store.save_report(session, project_id=project.id, content=content)
    return ReportResponse.model_validate(row, from_attributes=True)


@router.get("/reports/latest", response_model=ReportResponse | None)
async def get_latest_report(
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse | None:
    row = await analyses_store.latest_report(session, project_id=project.id)
    return ReportResponse.model_validate(row, from_attributes=True) if row else None
