"""CLI and API entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import json

import uvicorn

from app.agent.engine import AgentEngine
from app.api.app import create_app
from app.config.settings import get_settings
from app.core.logging import configure_logging
from app.database.engine import Database
from app.knowledge.store import KnowledgeStore
from app.memory.store import MemoryStore
from app.models.factory import create_model_provider, create_primary_provider
from app.projects import store as project_store
from app.projects.orchestrator import ProjectOrchestrator
from app.tools.builtin import build_default_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="MYAI agent platform")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("agent", help="Run one agent request locally against a scratch CLI project")
    run_parser.add_argument("input", help="User request")
    run_parser.add_argument("--project-id", default=None, help="Reuse an existing project id")

    serve_parser = sub.add_parser("serve", help="Start the FastAPI service")
    serve_parser.add_argument("--host", default=None)
    serve_parser.add_argument("--port", type=int, default=None)

    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)

    if args.command == "serve":
        uvicorn.run(
            "app.api.app:create_app",
            factory=True,
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
            reload=False,
        )
        return

    result = asyncio.run(_run_once(args.input, args.project_id))
    print(json.dumps(result, indent=2, default=str))


async def _run_once(user_input: str, project_id: str | None):
    settings = get_settings()
    db = Database(settings)
    await db.create_all()
    ollama_model = create_model_provider(settings)
    model = create_primary_provider(settings, ollama_fallback=ollama_model)
    memory_store = MemoryStore(db)
    knowledge_store = KnowledgeStore(db)
    tools = build_default_registry(settings, db=db, memory_store=memory_store, knowledge_store=knowledge_store, model=model)
    engine = AgentEngine(model=model, tools=tools, settings=settings)
    orchestrator = ProjectOrchestrator(
        engine=engine, db=db, model=model, memory=memory_store, settings=settings
    )

    async with db.session() as session:
        user = await project_store.get_user_by_email(session, "cli@local")
        if user is None:
            from app.security.auth import hash_password

            user = await project_store.create_user(
                session, name="CLI User", email="cli@local", password_hash=hash_password("cli-local-user")
            )
        if project_id:
            project = await project_store.get_owned_project(session, project_id=project_id, user_id=user.id)
        else:
            project = await project_store.create_project(session, user_id=user.id, fields={"name": "CLI Scratch Project"})
        conversation = await project_store.create_conversation(session, project_id=project.id)

    final: dict = {}
    async for event in orchestrator.run_stream(
        project=project, user_id=user.id, conversation_id=conversation.id, user_input=user_input
    ):
        if event["type"] == "done":
            final = event
    await db.dispose()
    return final


app = create_app()

if __name__ == "__main__":
    main()
