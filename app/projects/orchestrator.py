from __future__ import annotations

from typing import Any, AsyncIterator

from app.agent.engine import AgentEngine
from app.agent.router import needs_agent_path
from app.agent.types import AgentRequest
from app.database.engine import Database
from app.database.models import Project
from app.memory.store import MemoryStore
from app.models.base import ChatMessage, ModelProvider
from app.projects import analyses_store, store as project_store
from app.startup.extraction import extract_profile_updates
from app.startup.response_builder import build_response

ANALYSIS_TOOLS = {
    "market_research": "market_research",
    "competitor_research": "competitor_research",
    "financial_analysis": "financial_analysis",
    "startup_viability_predictor": "viability",
}

RECENT_MESSAGE_LIMIT = 16

ROLE_PROMPT = """You are an AI co-founder for a startup incubator platform.
You are working on ONE specific project right now. Only use the context given below for
THIS project — never invent facts from a different startup.

Choose whichever registered tools actually fit the user's request — do not run every tool for
every message. For a simple calculation, use only the calculator. For a competitor question,
use competitor_research. For a full evaluation, you may use market_research, competitor_research,
financial_analysis, and startup_viability_predictor together.

market_research, competitor_research, and financial_analysis each automatically search the live
web for real current Indian data (market stats, named competitors, real INR pricing) when you
give them the industry — you do not need to call web_search yourself before them; just pass
industry (and financial_analysis's industry field) and they ground themselves. Only call
web_search directly for other ad-hoc real-world questions that don't fit one of those tools.

You cannot generate the final startup report from chat — there is no report tool available to
you. If the user asks for a report or a full written summary, tell them to use the "Generate
Report" button on the project's Report page once they feel everything is ready; do not attempt
to produce a report yourself.

When calling startup_viability_predictor, NEVER leave the factors at their default value of 50.
Set each of the 8 factor arguments explicitly, scoring it 0-100 based on the specific evidence
already gathered in this conversation (market research, competitor research, financial analysis,
and the project profile). Two different projects must not receive identical factor scores —
if you have no evidence at all for a factor, reason about it from the industry and problem
description instead of defaulting to the middle.

Use memory_write to save confirmed facts/decisions/assumptions/risks about THIS project so future
conversations remember them. Only categorize something as a 'decision' if the founder actually
confirmed it.

When calling financial_analysis, always pass the industry field and leave initial_cost_components
/ monthly_cost_components empty so it can research real INR costs itself — only fill those in
yourself if the founder already gave you their own real numbers."""

INTAKE_PROMPT = """You are an AI co-founder for a startup incubator platform.
The founder just described their idea for THIS project for the very first time. Call ALL FOUR of
these tools, in order, using this message and the project profile below as the basis for each:
market_research, competitor_research, financial_analysis, then startup_viability_predictor. Do
not ask for permission or confirmation first, and do not skip any of them even if the founder's
message is short — infer what you can from the profile and industry.

market_research, competitor_research, and financial_analysis each automatically search the live
web for real current Indian data (market stats, named competitors, real INR pricing) when you
give them the industry — you do not need to call web_search yourself first; just pass industry to
each of them (and financial_analysis's industry field) and they ground themselves.

When calling startup_viability_predictor, NEVER leave the factors at their default value of 50.
Set each of the 8 factor arguments explicitly, scoring it 0-100 based on the evidence you just
gathered from the other three tools and the project profile. Two different projects must not
receive identical factor scores — reason from the industry and problem description rather than
defaulting to the middle.

You do NOT have a report tool available in this turn — never attempt to generate a report here.

When calling financial_analysis, always pass the industry field and leave initial_cost_components
/ monthly_cost_components empty so it can research real INR costs itself — only fill those in
yourself if the founder already gave you their own real numbers.

Once all four tools have returned results, write a short, warm, conversational summary (2-4
sentences) of what stood out — the strongest signal and the biggest risk — and ask the founder
what they'd like to focus on next. Do not just repeat raw numbers; talk like a co-founder giving
an update."""

FAST_PROMPT = """You are an AI co-founder for a startup incubator platform, having a normal
conversation about ONE specific project. Answer directly and conversationally using only the
project context below. Do not claim to have run research or tools you were not given results
from — if the user asks for research or calculations, tell them you can look into it.

If the user asks for a report, a full summary, or a written overview of everything gathered,
do NOT write one yourself, and do NOT list out the project profile or findings as if it were a
report. Instead reply with only something like: "I can't generate the report from here — head to
the Report page and click 'Generate Report' once you feel everything is ready.\""""

_INTAKE_TOOL_NAMES = [
    "web_search",
    "market_research",
    "competitor_research",
    "financial_analysis",
    "startup_viability_predictor",
]

_TOOL_LABELS = {
    "web_search": "Searching the web",
    "market_research": "Researching market",
    "competitor_research": "Analyzing competitors",
    "financial_analysis": "Calculating financials",
    "startup_viability_predictor": "Evaluating viability",
    "memory_write": "Saving project context",
    "memory_search": "Recalling project context",
    "calculator": "Calculating",
}


class ProjectOrchestrator:
    def __init__(
        self,
        *,
        engine: AgentEngine,
        db: Database,
        model: ModelProvider,
        memory: MemoryStore,
        settings,
    ):
        self.engine = engine
        self.db = db
        self.model = model
        self.memory = memory
        self.settings = settings

    async def _build_context_block(self, project: Project) -> str:
        profile_lines = "\n".join(
            f"- {label}: {value}"
            for label, value in (
                ("Name", project.name),
                ("Industry", project.industry),
                ("Stage", project.stage),
                ("Problem", project.problem),
                ("Solution", project.solution),
                ("Target customer", project.target_customer),
                ("Geography", project.geography),
                ("Business model", project.business_model),
                ("Budget", project.budget),
                ("Goals", project.goals),
            )
            if value
        )
        if not profile_lines:
            profile_lines = "No profile facts are known yet."

        memory_items = await self.memory.list_recent(project.id, limit=12)
        if memory_items:
            memory_lines = "\n".join(
                f"- [{item['category']}] {item['content']}" for item in memory_items
            )
        else:
            memory_lines = "No stored memory yet."

        return (
            f"PROJECT: {project.name}\n\n"
            f"PROJECT PROFILE:\n{profile_lines}\n\n"
            f"PROJECT MEMORY (facts/decisions/assumptions/risks):\n{memory_lines}"
        )

    async def _recent_history_messages(self, conversation_id: str) -> list[ChatMessage]:
        async with self.db.session() as session:
            rows = await project_store.recent_messages(
                session, conversation_id=conversation_id, limit=RECENT_MESSAGE_LIMIT
            )
        return [
            ChatMessage(role=row.role, content=row.content)
            for row in rows
            if row.role in ("user", "assistant")
        ]

    async def _has_no_analyses(self, project_id: str) -> bool:
        async with self.db.session() as session:
            market = await analyses_store.latest_market_research(session, project_id=project_id)
            financial = await analyses_store.latest_financial_analysis(session, project_id=project_id)
            viability = await analyses_store.latest_viability(session, project_id=project_id)
            competitors = await analyses_store.list_competitors(session, project_id=project_id)
        return not (market or financial or viability or competitors)

    async def run_stream(
        self,
        *,
        project: Project,
        user_id: str,
        conversation_id: str,
        user_input: str,
    ) -> AsyncIterator[dict[str, Any]]:
        async with self.db.session() as session:
            await project_store.add_message(
                session, conversation_id=conversation_id, role="user", content=user_input
            )
            await project_store.touch_project(session, project=project)

        context_block = await self._build_context_block(project)
        history = await self._recent_history_messages(conversation_id)

        if len(history) == 1 and await self._has_no_analyses(project.id):
            async for event in self._run_agent_path(
                project=project,
                user_id=user_id,
                conversation_id=conversation_id,
                user_input=user_input,
                context_block=context_block,
                system_prompt=INTAKE_PROMPT,
                tool_names=_INTAKE_TOOL_NAMES,
            ):
                yield event
        elif needs_agent_path(user_input):
            async for event in self._run_agent_path(
                project=project,
                user_id=user_id,
                conversation_id=conversation_id,
                user_input=user_input,
                context_block=context_block,
            ):
                yield event
        else:
            async for event in self._run_fast_path(
                project_id=project.id,
                conversation_id=conversation_id,
                user_input=user_input,
                context_block=context_block,
                history=history,
            ):
                yield event

    async def _run_fast_path(
        self,
        *,
        project_id: str,
        conversation_id: str,
        user_input: str,
        context_block: str,
        history: list[ChatMessage],
    ) -> AsyncIterator[dict[str, Any]]:
        # `history` already includes the just-persisted current user message.
        messages = [
            ChatMessage(role="system", content=f"{FAST_PROMPT}\n\n{context_block}"),
            *(history or [ChatMessage(role="user", content=user_input)]),
        ]
        chunks: list[str] = []
        async for token in self.model.chat_stream(
            messages,
            temperature=self.settings.model_temperature,
            max_tokens=self.settings.fast_path_max_tokens,
        ):
            chunks.append(token)
            yield {"type": "token", "text": token}

        output = "".join(chunks).strip() or "I didn't produce a response — please try again."
        async with self.db.session() as session:
            await project_store.add_message(
                session, conversation_id=conversation_id, role="assistant", content=output
            )
        yield {
            "type": "done",
            "path": "fast",
            "response": output,
            "project_id": project_id,
            "conversation_id": conversation_id,
            "tool_activity": [],
            "analysis": None,
            "viability": None,
            "recommendations": [],
            "sources": [],
            "errors": [],
            "success": True,
        }

    async def _run_agent_path(
        self,
        *,
        project: Project,
        user_id: str,
        conversation_id: str,
        user_input: str,
        context_block: str,
        system_prompt: str = ROLE_PROMPT,
        tool_names: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "status", "message": "Thinking..."}

        updates = await extract_profile_updates(self.model, user_input)
        if not updates.is_empty():
            async with self.db.session() as session:
                project = await project_store.merge_profile_fields(
                    session, project=project, fields=updates.to_project_fields()
                )
            context_block = await self._build_context_block(project)

        result = await self.engine.run(
            AgentRequest(
                input=user_input,
                user_id=user_id,
                project_id=project.id,
                conversation_id=conversation_id,
            ),
            extra_system_context=f"{system_prompt}\n\n{context_block}",
            tool_names=tool_names,
        )

        for event in result.tool_events:
            label = _TOOL_LABELS.get(event.name, event.name.replace("_", " ").title())
            status_msg = f"{label} completed" if event.status == "ok" else f"{label} failed"
            yield {"type": "status", "message": status_msg}

        await self._persist_analyses(result, project.id)

        async with self.db.session() as session:
            await project_store.add_message(
                session, conversation_id=conversation_id, role="assistant", content=result.output
            )

        response = build_response(result=result, project=project)
        response["conversation_id"] = conversation_id

        yield {"type": "token", "text": result.output}
        yield {"type": "done", "path": "agent", **response}

    async def _persist_analyses(self, result, project_id: str) -> None:
        async with self.db.session() as session:
            for event in result.tool_events:
                if event.status != "ok" or not event.result:
                    continue
                if event.name == "market_research":
                    await analyses_store.save_market_research(
                        session, project_id=project_id, data=event.result
                    )
                elif event.name == "competitor_research":
                    competitors = event.result.get("competitors")
                    if isinstance(competitors, list) and competitors:
                        await analyses_store.replace_competitors_from_research(
                            session, project_id=project_id, competitors=competitors
                        )
                elif event.name == "financial_analysis":
                    await analyses_store.save_financial_analysis(
                        session, project_id=project_id, data=event.result
                    )
                elif event.name == "startup_viability_predictor":
                    await analyses_store.save_viability(
                        session, project_id=project_id, data=event.result
                    )
