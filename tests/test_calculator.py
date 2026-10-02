from app.tools.builtin.calculator import CalculatorTool
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry
import pytest


@pytest.mark.asyncio
async def test_calculator_multiplies():
    tool = CalculatorTool()
    result = await tool.run(
        {"expression": "125 × 48"},
        ToolContext(user_id="user_1", project_id="proj_1", run_id="run_test"),
    )
    assert result["result"] == 6000.0


@pytest.mark.asyncio
async def test_calculator_rejects_code():
    tool = CalculatorTool()
    with pytest.raises(Exception):
        await tool.run(
            {"expression": "__import__('os').system('echo hi')"},
            ToolContext(user_id="user_1", project_id="proj_1", run_id="run_test"),
        )


@pytest.mark.asyncio
async def test_registry_discovers_calculator():
    from app.tools.builtin import build_default_registry

    registry = build_default_registry()
    names = [item["name"] for item in registry.list_metadata()]
    assert "calculator" in names
