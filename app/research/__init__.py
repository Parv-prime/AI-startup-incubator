"""Live research: provider-independent web search + page reading.

    research tool → ResearchProvider (cache → fallback chain) → Tavily / Exa / DuckDuckGo
"""

from app.research.base import (
    UNAVAILABLE_MESSAGE,
    ResearchProvider,
    ResearchProviderError,
    ResearchUnavailableError,
    Source,
)
from app.research.factory import create_research_provider

__all__ = [
    "UNAVAILABLE_MESSAGE",
    "ResearchProvider",
    "ResearchProviderError",
    "ResearchUnavailableError",
    "Source",
    "create_research_provider",
]
