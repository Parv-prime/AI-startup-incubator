from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse
from ml import predictor

router = APIRouter(tags=["health"])


@router.get("/api/v1/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    model = request.app.state.model
    llm_reachable = await model.health()

    database_status = "ok"
    try:
        db = request.app.state.db
        async with db.session() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    ml_model_status = "ready" if predictor.is_available() else "not_trained"

    overall = "ok" if llm_reachable and database_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        version="0.1.0",
        model_runtime=settings.model_runtime,
        model_name=settings.model_name,
        llm_status="reachable" if llm_reachable else "unreachable",
        database_status=database_status,
        ml_model_status=ml_model_status,
    )
