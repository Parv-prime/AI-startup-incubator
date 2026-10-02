from __future__ import annotations

import pytest

from app.agent.engine import AgentEngine
from app.agent.types import AgentRequest
from app.config.settings import Settings
from app.models.base import ChatMessage, ModelResponse, ToolCall, ToolSpec
from app.tools.builtin import build_default_registry


class ScriptedModel:
    name = "scripted"
    runtime = "test"

    def __init__(self) -> None:
        self.step = 0

    async def health(self) -> bool:
        return True

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        self.step += 1
        if self.step == 1:
            return ModelResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="calculator",
                        arguments={"expression": "125 * 48"},
                    )
                ],
            )
        last = messages[-1]
        return ModelResponse(content=f"The product is {last.content}.")


@pytest.mark.asyncio
async def test_agent_uses_calculator_and_observes_result():
    settings = Settings(max_agent_iterations=4, agent_timeout_seconds=10)
    engine = AgentEngine(
        model=ScriptedModel(),
        tools=build_default_registry(),
        settings=settings,
    )
    result = await engine.run(
        AgentRequest(input="Calculate 125 × 48.", user_id="user_1", project_id="proj_1")
    )
    assert result.status == "completed"
    assert result.tool_events[0].name == "calculator"
    assert result.tool_events[0].status == "ok"
    assert result.tool_events[0].result["result"] == 6000.0
    assert "6000" in result.output
