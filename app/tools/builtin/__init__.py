from app.config.settings import Settings
from app.database.engine import Database
from app.knowledge.store import KnowledgeStore
from app.knowledge.tools import KnowledgeSearchTool
from app.memory.store import MemoryStore
from app.memory.tools import MemorySearchTool, MemoryWriteTool
from app.models.base import ModelProvider
from app.research import ResearchProvider, create_research_provider
from app.tools.builtin.calculator import CalculatorTool
from app.tools.builtin.competitor_research import CompetitorResearchTool
from app.tools.builtin.file_reader import FileReaderTool
from app.tools.builtin.financial_analysis import FinancialAnalysisTool
from app.tools.builtin.market_research import MarketResearchTool
from app.tools.builtin.text_processor import TextProcessorTool
from app.tools.builtin.viability_predictor import ViabilityPredictorTool
from app.tools.builtin.web_search import WebSearchTool
from app.tools.registry import ToolRegistry


def build_default_registry(
    settings: Settings | None = None,
    *,
    db: Database | None = None,
    memory_store: MemoryStore | None = None,
    knowledge_store: KnowledgeStore | None = None,
    model: ModelProvider | None = None,
    research: ResearchProvider | None = None,
) -> ToolRegistry:
    settings = settings or Settings()
    research = research or create_research_provider(settings)
    # Sources shown to the LLM per research request; kept small so prompts fit a
    # 3B local model's context window as well as cloud models.
    max_sources = max(1, min(settings.research_max_results + 1, 8))

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(TextProcessorTool())
    registry.register(FileReaderTool())
    registry.register(FinancialAnalysisTool(model, research))
    registry.register(WebSearchTool(research))
    if db is not None:
        memory_store = memory_store or MemoryStore(db)
        knowledge_store = knowledge_store or KnowledgeStore(db)
        registry.register(MemoryWriteTool(memory_store))
        registry.register(MemorySearchTool(memory_store))
        registry.register(KnowledgeSearchTool(knowledge_store))
        registry.register(ViabilityPredictorTool(db))
    if model is not None:
        registry.register(
            MarketResearchTool(
                model,
                research,
                max_results=settings.research_max_results,
                max_sources=max_sources,
            )
        )
        registry.register(
            CompetitorResearchTool(
                model,
                research,
                max_results=settings.research_max_results,
                max_sources=max_sources,
                max_fetched_pages=settings.research_max_fetched_pages,
            )
        )
    return registry
