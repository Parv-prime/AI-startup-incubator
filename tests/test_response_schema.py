from __future__ import annotations

from app.agent.types import AgentResult, ToolEvent
from app.database.models import Project
from app.startup.response_builder import build_response


def _project(**kwargs) -> Project:
    project = Project(id="proj_1", user_id="user_1", name="Test Startup")
    for key, value in kwargs.items():
        setattr(project, key, value)
    return project


def test_build_response_extracts_viability_and_recommendations():
    result = AgentResult(
        run_id="run_1",
        project_id="proj_1",
        status="completed",
        output="Here is your evaluation.",
        iterations=2,
        tool_events=[
            ToolEvent(
                name="financial_analysis",
                arguments={},
                status="ok",
                result={"monthly_profit_loss": -500, "runway_months": 10},
                duration_ms=5.0,
            ),
            ToolEvent(
                name="startup_viability_predictor",
                arguments={},
                status="ok",
                result={
                    "score": 42.0,
                    "classification": "Low Potential",
                    "factors": {"market_demand": 30, "competition": 60},
                    "feature_importance": {"market_demand": 0.5, "competition": 0.5},
                    "model_version": "1.0.0",
                },
                duration_ms=3.0,
            ),
        ],
    )
    response = build_response(result=result, project=_project(industry="EdTech"))
    assert response["success"] is True
    assert response["viability"]["score"] == 42.0
    assert response["project_id"] == "proj_1"
    assert len(response["tool_activity"]) == 2
    assert any(rec["category"] == "Finance" for rec in response["recommendations"])
    assert any(rec["category"] == "Viability" for rec in response["recommendations"])


def test_build_response_handles_no_tools_used():
    result = AgentResult(
        run_id="run_2",
        project_id="proj_1",
        status="completed",
        output="Hello!",
        iterations=1,
        tool_events=[],
    )
    response = build_response(result=result, project=_project())
    assert response["viability"] is None
    assert response["analysis"] is None
    assert response["tool_activity"] == []
