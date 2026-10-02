from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.engine import AgentEngine
from app.api.routers import auth, conversations, health, knowledge, memory, project_data, projects, tools
from app.config.settings import Settings, get_settings
from app.database.engine import Database
from app.knowledge.store import KnowledgeStore
from app.memory.store import MemoryStore
from app.models.factory import create_model_provider, create_primary_provider
from app.projects.orchestrator import ProjectOrchestrator
from app.tools.builtin import build_default_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    db = Database(settings)
    await db.create_all()

    ollama_model = create_model_provider(settings)
    # Gemini (key 1, then key 2) drives every chat/tool-calling call; Ollama is
    # only ever reached as a backup if Gemini is unset or both keys fail.
    model = create_primary_provider(settings, ollama_fallback=ollama_model)
    memory_store = MemoryStore(db)
    knowledge_store = KnowledgeStore(db)
    registry = build_default_registry(
        settings,
        db=db,
        memory_store=memory_store,
        knowledge_store=knowledge_store,
        model=model,
    )
    engine = AgentEngine(model=model, tools=registry, settings=settings)

    app.state.settings = settings
    app.state.db = db
    app.state.model = model
    app.state.memory = memory_store
    app.state.knowledge = knowledge_store
    app.state.tools = registry
    app.state.agent = engine
    app.state.orchestrator = ProjectOrchestrator(
        engine=engine,
        db=db,
        model=model,
        memory=memory_store,
        settings=settings,
    )
    yield
    await db.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Startup Incubator",
        version="0.1.0",
        description="Multi-project AI startup incubator platform.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(conversations.router)
    app.include_router(project_data.router)
    app.include_router(tools.router)
    app.include_router(memory.router)
    app.include_router(knowledge.router)
    return app
