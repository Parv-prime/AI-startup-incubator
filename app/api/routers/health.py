from fastapi import APIRouter, Request

from app.api.schemas import HealthResponse
from ml import predictor

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Cheap liveness probe for the hosting platform (Render health check).

    Makes no LLM, research or database calls, so it is fast and never spends
    provider quota.
    """
    return {"status": "ok"}


@router.get("/api/v1/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Detailed status for the frontend Settings page. Exposes only non-secret info:
    provider type, model name and reachability — never keys, URLs or env values."""
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

    research = getattr(request.app.state, "research", None)
    research_providers = list(getattr(research, "provider_names", []) or [])

    overall = "ok" if llm_reachable and database_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        version="0.1.0",
        model_runtime=model.runtime,
        model_name=model.name,
        llm_status="reachable" if llm_reachable else "unreachable",
        database_status=database_status,
        ml_model_status=ml_model_status,
        research_status="configured" if research_providers else "unavailable",
        research_providers=research_providers,
    )
