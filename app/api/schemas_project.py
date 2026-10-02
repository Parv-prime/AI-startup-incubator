from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProjectCreateRequest(BaseModel):
    name: str
    description: str | None = None
    industry: str | None = None
    stage: str | None = None
    target_customer: str | None = None
    geography: str | None = None
    business_model: str | None = None
    problem: str | None = None
    solution: str | None = None
    budget: str | None = None
    goals: str | None = None


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    industry: str | None = None
    stage: str | None = None
    target_customer: str | None = None
    geography: str | None = None
    business_model: str | None = None
    problem: str | None = None
    solution: str | None = None
    budget: str | None = None
    goals: str | None = None
    status: str | None = None
    archived: bool | None = None


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None = None
    industry: str | None = None
    stage: str | None = None
    target_customer: str | None = None
    geography: str | None = None
    business_model: str | None = None
    problem: str | None = None
    solution: str | None = None
    budget: str | None = None
    goals: str | None = None
    status: str
    archived: bool
    created_at: datetime
    updated_at: datetime
    last_active_at: datetime

    model_config = {"from_attributes": True}
