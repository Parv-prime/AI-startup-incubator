from app.config.settings import Settings
from app.core.errors import ModelConfigurationError
from app.core.logging import get_logger
from app.models.base import ModelProvider
from app.models.runtimes.cloud import CloudLLMProvider
from app.models.runtimes.fallback import FallbackChatProvider
from app.models.runtimes.ollama import OllamaProvider
from app.models.runtimes.pool import ProviderPool

logger = get_logger(__name__)

SUPPORTED_PROVIDERS = ("ollama", "cloud")


def create_model_provider(settings: Settings) -> ModelProvider:
    """Build the single ModelProvider the whole app uses (agent, tools, chat).

    Selection comes only from configuration (LLM_PROVIDER), so the same code runs
    locally against Ollama and in production against the configured cloud LLM.
    """
    name = settings.llm_provider.strip().lower()
    primary = _build(name, settings)

    fallback_name = settings.llm_fallback_provider.strip().lower()
    if not fallback_name or fallback_name == name:
        return primary
    if fallback_name != "ollama":
        raise ModelConfigurationError(
            f"Unsupported LLM_FALLBACK_PROVIDER '{settings.llm_fallback_provider}'. Supported: ollama",
        )
    logger.info("llm_fallback_enabled", extra={"primary": name, "fallback": fallback_name})
    return FallbackChatProvider(primary=primary, fallback=_build(fallback_name, settings))


def _build(name: str, settings: Settings) -> ModelProvider:
    if name == "ollama":
        # Capped independently of the overall agent budget: a single slow model
        # call must not be able to silently outlast (or barely undercut) the
        # engine's own asyncio.wait_for deadline.
        per_call_timeout = min(240.0, float(settings.agent_timeout_seconds))
        return OllamaProvider(
            model_name=settings.ollama_model,
            base_url=settings.ollama_base_url,
            timeout=per_call_timeout,
        )
    if name == "cloud":
        return _build_cloud(settings)
    raise ModelConfigurationError(
        f"Unknown LLM_PROVIDER '{name}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        details={"provider": name},
    )


def _split_keys(value: str) -> list[str]:
    return [key.strip() for key in value.split(",") if key.strip()]


def _build_cloud(settings: Settings) -> ModelProvider:
    """One provider per configured key, in failover order: CLOUD_LLM_* → Groq → Gemini."""
    timeout = settings.cloud_llm_timeout_seconds
    providers: list[ModelProvider] = []

    generic = (
        ("CLOUD_LLM_BASE_URL", settings.cloud_llm_base_url),
        ("CLOUD_LLM_MODEL", settings.cloud_llm_model),
        ("CLOUD_LLM_API_KEY", settings.cloud_llm_api_key),
    )
    missing = [env_name for env_name, value in generic if not value.strip()]
    if not missing:
        for i, key in enumerate(_split_keys(settings.cloud_llm_api_key), start=1):
            providers.append(
                CloudLLMProvider(
                    base_url=settings.cloud_llm_base_url,
                    api_key=key,
                    model_name=settings.cloud_llm_model,
                    timeout=timeout,
                    reasoning_effort=settings.cloud_llm_reasoning_effort,
                    label=f"cloud#{i}",
                )
            )

    for vendor, base_url, model, keys in (
        ("groq", settings.groq_base_url, settings.groq_model, settings.groq_api_keys),
        ("gemini", settings.gemini_base_url, settings.gemini_model, settings.gemini_api_keys),
    ):
        for i, key in enumerate(_split_keys(keys), start=1):
            providers.append(
                CloudLLMProvider(
                    base_url=base_url, api_key=key, model_name=model, timeout=timeout, label=f"{vendor}#{i}"
                )
            )

    if not providers:
        raise ModelConfigurationError(
            "LLM_PROVIDER=cloud but no cloud LLM is configured. Set GROQ_API_KEYS and/or "
            "GEMINI_API_KEYS, or all of CLOUD_LLM_BASE_URL, CLOUD_LLM_MODEL and CLOUD_LLM_API_KEY "
            f"(not set: {', '.join(missing)}).",
            details={"missing": missing},
        )
    if 0 < len(missing) < len(generic):
        logger.warning("cloud_llm_partially_configured_skipped", extra={"missing": missing})
    logger.info("cloud_llm_providers", extra={"order": [p.label for p in providers]})
    return providers[0] if len(providers) == 1 else ProviderPool(providers)
