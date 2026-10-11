from __future__ import annotations

from app.config.settings import Settings
from app.core.logging import get_logger
from app.research.base import ResearchProvider
from app.research.cache import CachedResearchProvider
from app.research.fallback import FallbackResearchProvider
from app.research.providers.duckduckgo import DuckDuckGoProvider
from app.research.providers.exa import ExaProvider
from app.research.providers.tavily import TavilyProvider
from app.research.reader import DirectPageReader, JinaReader

logger = get_logger(__name__)

SUPPORTED_PROVIDERS = ("tavily", "exa", "duckduckgo")


def create_research_provider(settings: Settings) -> ResearchProvider:
    """Build the provider chain from RESEARCH_PROVIDER + RESEARCH_FALLBACK_PROVIDERS.

    Providers whose API key is missing are skipped (with a log line) rather
    than failing on every request. DuckDuckGo needs no key.
    """
    timeout = settings.research_timeout_seconds
    max_chars = settings.research_max_chars_per_source
    providers: list[ResearchProvider] = []
    skipped: list[str] = []

    for name in settings.research_provider_order:
        if name == "tavily":
            if settings.tavily_api_key:
                providers.append(
                    TavilyProvider(
                        api_key=settings.tavily_api_key,
                        search_depth=settings.tavily_search_depth,
                        timeout=timeout,
                        max_chars=max_chars,
                    )
                )
            else:
                skipped.append("tavily (TAVILY_API_KEY not set)")
        elif name == "exa":
            if settings.exa_api_key:
                providers.append(ExaProvider(api_key=settings.exa_api_key, timeout=timeout, max_chars=max_chars))
            else:
                skipped.append("exa (EXA_API_KEY not set)")
        elif name == "duckduckgo":
            providers.append(DuckDuckGoProvider(timeout=min(timeout, 10.0), max_chars=max_chars))
        elif name in ("none", "off", "disabled"):
            continue
        else:
            skipped.append(f"{name} (unknown provider; supported: {', '.join(SUPPORTED_PROVIDERS)})")

    fetch_timeout = settings.research_fetch_timeout_seconds
    readers = []
    if settings.jina_reader_enabled:
        readers.append(JinaReader(api_key=settings.jina_api_key, timeout=fetch_timeout, max_chars=max_chars))
    readers.append(DirectPageReader(timeout=fetch_timeout, max_chars=max_chars))

    logger.info(
        "research_providers_configured",
        extra={"active": [p.name for p in providers], "skipped": skipped},
    )
    if not providers:
        logger.warning("research_disabled_no_providers", extra={"skipped": skipped})

    chain: ResearchProvider = FallbackResearchProvider(providers, readers)
    if settings.research_cache_enabled and settings.research_cache_ttl_seconds > 0:
        chain = CachedResearchProvider(chain, ttl_seconds=settings.research_cache_ttl_seconds)
    return chain
