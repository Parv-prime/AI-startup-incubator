from __future__ import annotations

import pytest

from app.core.errors import ToolValidationError
from app.tools.base import ToolContext
from app.tools.builtin import build_default_registry


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected():
    registry = build_default_registry()
    context = ToolContext(user_id="user_1", project_id="proj_1", run_id="run_1")
    with pytest.raises(ToolValidationError):
        await registry.execute("delete_everything", {}, context)


@pytest.mark.asyncio
async def test_invalid_arguments_are_rejected():
    registry = build_default_registry()
    context = ToolContext(user_id="user_1", project_id="proj_1", run_id="run_1")
    with pytest.raises(ToolValidationError):
        await registry.execute("financial_analysis", {"monthly_operating_cost": "not-a-number"}, context)
