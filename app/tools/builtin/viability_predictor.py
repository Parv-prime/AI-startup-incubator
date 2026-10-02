from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import ToolExecutionError
from app.database.engine import Database
from app.projects import analyses_store, store as project_store
from app.startup.viability_features import derive_features
from app.tools.base import BaseTool, ToolContext
from app.tools.permissions import PermissionLevel
from ml import predictor


def _score_field(description: str) -> Any:
    return Field(default=None, ge=0, le=100, description=description)


class ViabilityInput(BaseModel):
    market_demand: float | None = _score_field(
        "Override 0-100: strength of demand. Omit to derive from gathered market research."
    )
    competition: float | None = _score_field(
        "Override 0-100: competitive intensity (higher = more crowded). Omit to derive from gathered competitor research."
    )
    problem_severity: float | None = _score_field(
        "Override 0-100: how painful/urgent the problem is. Omit to derive from the startup profile."
    )
    customer_accessibility: float | None = _score_field(
        "Override 0-100: how easily the target customer can be reached. Omit to derive from the profile."
    )
    business_model_strength: float | None = _score_field(
        "Override 0-100: soundness of the revenue model. Omit to derive from gathered financials."
    )
    startup_cost: float | None = _score_field(
        "Override 0-100 affordability (higher = cheaper to start). Omit to derive from gathered financials."
    )
    scalability: float | None = _score_field(
        "Override 0-100: ability to grow without linear cost growth. Omit to derive from the profile."
    )
    growth_potential: float | None = _score_field(
        "Override 0-100: size of the long-term opportunity. Omit to derive from gathered market research."
    )


class ViabilityOutput(BaseModel):
    score: float
    classification: str
    factors: dict[str, float]
    feature_importance: dict[str, float]
    model_version: str


class ViabilityPredictorTool(BaseTool):
    name = "startup_viability_predictor"
    description = (
        "Estimate a 0-100 startup viability score using a trained ML model. Factor scores are "
        "derived automatically from the market/competitor/financial research already gathered "
        "for this project — only pass an argument if you want to explicitly override one factor "
        "with your own judgment. This is an educational decision-support estimate, not a "
        "prediction of real-world success."
    )
    permission = PermissionLevel.READ_ONLY
    input_model = ViabilityInput
    output_model = ViabilityOutput

    def __init__(self, db: Database):
        self.db = db

    async def execute(self, payload: ViabilityInput, context: ToolContext) -> dict[str, Any]:
        if not predictor.is_available():
            raise ToolExecutionError(
                "The viability model is not trained yet. Run "
                "`python ml/train/train_viability_model.py`."
            )

        async with self.db.session() as session:
            project = await project_store.get_project(session, project_id=context.project_id)
            market_row = await analyses_store.latest_market_research(session, project_id=context.project_id)
            financial_row = await analyses_store.latest_financial_analysis(
                session, project_id=context.project_id
            )
            competitors = await analyses_store.list_competitors(session, project_id=context.project_id)

        market = market_row.data if market_row else None
        financial = financial_row.data if financial_row else None
        competitor = {"competitors": [{"name": c.name} for c in competitors]} if competitors else None

        derived = derive_features(profile=project, market=market, competitor=competitor, financial=financial)
        overrides = {k: v for k, v in payload.model_dump().items() if v is not None}
        features = {**derived, **overrides}

        return predictor.predict(features)
