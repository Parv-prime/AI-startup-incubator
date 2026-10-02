from __future__ import annotations

from pydantic import BaseModel


class ProfileUpdate(BaseModel):
    """Fields the LLM extracted from a single user message. Maps onto Project columns
    (startup_name -> name, startup_stage -> stage) when merged via
    app.projects.store.merge_profile_fields."""

    startup_name: str | None = None
    industry: str | None = None
    problem: str | None = None
    solution: str | None = None
    target_customer: str | None = None
    geography: str | None = None
    business_model: str | None = None
    startup_stage: str | None = None
    budget: str | None = None
    goals: str | None = None

    def is_empty(self) -> bool:
        return not any(self.model_dump().values())

    def to_project_fields(self) -> dict:
        data = self.model_dump()
        name = data.pop("startup_name")
        stage = data.pop("startup_stage")
        fields = {"name": name, "stage": stage, **data}
        return {key: value for key, value in fields.items() if value}
