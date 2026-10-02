from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.agent.types import AgentRequest, AgentResult, ToolEvent
from app.config.settings import Settings
from app.core.errors import AgentCancelledError, AgentError, AgentTimeoutError, MaxIterationsError
from app.core.ids import new_id
from app.core.logging import get_logger
from app.models.base import ChatMessage, ModelProvider
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a task-executing agent, not a chatbot that guesses.

Rules:
- Understand the user's objective.
- If a tool can produce a reliable result, you MUST use it.
- For arithmetic, always call the calculator tool. Do not compute by hand.
- Use memory_write / memory_search only for this application's facts.
- Use knowledge_search for stored documents. Use file_reader only for files inside data/knowledge.
- After a tool result arrives, use it. Do not ignore it.
- Return a concise final answer to the user.
- Never claim you executed a tool unless you actually did.
- Never execute operating-system commands or generated Python code.
"""


class AgentEngine:
    def __init__(
        self,
        *,
        model: ModelProvider,
        tools: ToolRegistry,
        settings: Settings,
    ):
        self.model = model
        self.tools = tools
        self.settings = settings

    async def run(
        self,
        request: AgentRequest,
        *,
        cancel_event: asyncio.Event | None = None,
        extra_system_context: str | None = None,
        tool_names: list[str] | None = None,
    ) -> AgentResult:
        run_id = new_id("run")
        started = time.monotonic()
        deadline = started + self.settings.agent_timeout_seconds
        system_content = SYSTEM_PROMPT
        if extra_system_context:
            system_content = f"{SYSTEM_PROMPT}\n\n{extra_system_context}"
        messages = [
            ChatMessage(role="system", content=system_content),
            ChatMessage(role="user", content=request.input),
        ]
        events: list[ToolEvent] = []
        tool_calls_used = 0

        logger.info(
            "agent_start",
            extra={
                "run_id": run_id,
                "project_id": request.project_id,
            },
        )

        try:
            for iteration in range(1, self.settings.max_agent_iterations + 1):
                _check_limits(deadline, cancel_event)
                remaining = max(1.0, deadline - time.monotonic())
                response = await asyncio.wait_for(
                    self.model.chat(
                        messages,
                        self.tools.specs(tool_names),
                        temperature=self.settings.model_temperature,
                        max_tokens=self.settings.model_max_tokens,
                    ),
                    timeout=remaining,
                )

                if response.tool_calls:
                    messages.append(
                        ChatMessage(
                            role="assistant",
                            content=response.content,
                            tool_calls=response.tool_calls,
                        )
                    )
                    for call in response.tool_calls:
                        if tool_calls_used >= self.settings.max_tool_calls_per_run:
                            raise MaxIterationsError("Tool execution limit reached.")
                        tool_calls_used += 1
                        event = await self._execute_tool(call.name, call.arguments, request, run_id)
                        events.append(event)
                        messages.append(
                            ChatMessage(
                                role="tool",
                                name=call.name,
                                tool_call_id=call.id,
                                content=json.dumps(event.model_dump(), default=str),
                            )
                        )
                    continue

                output = (response.content or "").strip()
                if not output:
                    output = "The agent finished without producing a response."
                logger.info(
                    "agent_complete",
                    extra={
                        "run_id": run_id,
                        "project_id": request.project_id,
                        "iterations": iteration,
                        "tools": [event.name for event in events],
                    },
                )
                return AgentResult(
                    run_id=run_id,
                    project_id=request.project_id,
                    status="completed",
                    output=output,
                    iterations=iteration,
                    tool_events=events,
                )

            raise MaxIterationsError("The agent reached the maximum iteration limit.")
        except asyncio.TimeoutError as exc:
            error = AgentTimeoutError("The agent exceeded its timeout.")
            return _failure(run_id, request, events, error)
        except AgentError as exc:
            return _failure(run_id, request, events, exc)

    async def _execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        request: AgentRequest,
        run_id: str,
    ) -> ToolEvent:
        started = time.perf_counter()
        context = ToolContext(
            user_id=request.user_id,
            project_id=request.project_id,
            run_id=run_id,
            confirmed=request.confirmed,
        )
        try:
            result = await self.tools.execute(name, arguments, context)
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "tool_ok",
                extra={"run_id": run_id, "tool": name, "duration_ms": round(duration_ms, 2)},
            )
            return ToolEvent(
                name=name,
                arguments=arguments,
                status="ok",
                result=result,
                duration_ms=round(duration_ms, 2),
            )
        except AgentError as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "tool_error",
                extra={"run_id": run_id, "tool": name, "error": exc.code},
            )
            return ToolEvent(
                name=name,
                arguments=arguments,
                status="error",
                error=exc.message,
                duration_ms=round(duration_ms, 2),
            )


def _check_limits(deadline: float, cancel_event: asyncio.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise AgentCancelledError("The agent run was cancelled.")
    if time.monotonic() >= deadline:
        raise AgentTimeoutError("The agent exceeded its timeout.")


def _failure(
    run_id: str,
    request: AgentRequest,
    events: list[ToolEvent],
    error: AgentError,
) -> AgentResult:
    return AgentResult(
        run_id=run_id,
        project_id=request.project_id,
        status="failed",
        output=error.message,
        iterations=len(events),
        tool_events=events,
        error_code=error.code,
        recoverable=error.recoverable,
    )
