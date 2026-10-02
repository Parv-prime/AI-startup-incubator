from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MarketResearchResponse(BaseModel):
    id: str
    project_id: str
    data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CompetitorResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str | None = None
    product: str | None = None
    pricing: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    target_market: str | None = None
    differentiation: str | None = None
    source: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CompetitorCreateRequest(BaseModel):
    name: str
    description: str | None = None
    product: str | None = None
    pricing: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    target_market: str | None = None
    differentiation: str | None = None
    source: str | None = None


class FinancialAnalysisResponse(BaseModel):
    id: str
    project_id: str
    data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ViabilityResponse(BaseModel):
    id: str
    project_id: str
    score: float
    classification: str
    factors: dict[str, float]
    feature_importance: dict[str, float]
    model_version: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RoadmapItemCreateRequest(BaseModel):
    phase: str | None = None
    title: str
    description: str | None = None
    priority: str = "Medium"
    status: str = "Pending"
    target_date: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    notes: str | None = None


class RoadmapItemUpdateRequest(BaseModel):
    phase: str | None = None
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    target_date: str | None = None
    dependencies: list[str] | None = None
    notes: str | None = None


class RoadmapItemResponse(BaseModel):
    id: str
    project_id: str
    phase: str | None = None
    title: str
    description: str | None = None
    priority: str
    status: str
    target_date: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    priority: str
    category: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: str
    project_id: str
    content: dict
    generated_at: datetime

    model_config = {"from_attributes": True}
