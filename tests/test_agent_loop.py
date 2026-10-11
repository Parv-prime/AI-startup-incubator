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


class RepeatingModel(ScriptedModel):
    async def chat(self, messages, tools=None, *, temperature=None, max_tokens=None):
        self.step += 1
        if self.step <= 2:
            return ModelResponse(
                content=None,
                tool_calls=[ToolCall(id=f"call_{self.step}", name="calculator", arguments={"expression": "2*3"})],
            )
        return ModelResponse(content="done")


@pytest.mark.asyncio
async def test_identical_repeat_tool_call_is_not_re_executed():
    settings = Settings(max_agent_iterations=5, agent_timeout_seconds=10)
    engine = AgentEngine(model=RepeatingModel(), tools=build_default_registry(), settings=settings)
    result = await engine.run(AgentRequest(input="2*3", user_id="u", project_id="p"))
    assert result.status == "completed"
    assert [e.name for e in result.tool_events] == ["calculator"]


def test_collapse_repetition_removes_looping_sentences():
    from app.agent.engine import collapse_repetition

    looped = "Live research is currently unavailable. " * 6 + "Try again later."
    assert collapse_repetition(looped) == "Live research is currently unavailable. Try again later."
    normal = "Line one is here.\n\nLine two is different."
    assert collapse_repetition(normal) == normal
