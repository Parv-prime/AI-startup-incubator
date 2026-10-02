from app.config.settings import Settings
from app.core.errors import FatalError
from app.models.base import ModelProvider
from app.models.runtimes.fallback import FallbackChatProvider
from app.models.runtimes.groq import GroqProvider
from app.models.runtimes.ollama import OllamaProvider


def create_model_provider(settings: Settings) -> ModelProvider:
    runtime = settings.model_runtime.lower()
    if runtime == "ollama":
        # Capped independently of the overall agent budget: a single slow model
        # call must not be able to silently outlast (or barely undercut) the
        # engine's own asyncio.wait_for deadline.
        per_call_timeout = min(240.0, float(settings.agent_timeout_seconds))
        return OllamaProvider(
            model_name=settings.model_name,
            base_url=settings.ollama_base_url,
            timeout=per_call_timeout,
        )
    raise FatalError(
        f"Unknown MODEL_RUNTIME '{settings.model_runtime}'. Supported: ollama",
        details={"runtime": settings.model_runtime},
    )


def create_primary_provider(settings: Settings, *, ollama_fallback: ModelProvider) -> ModelProvider:
    """Provider used everywhere (quick chat AND the tool-calling agent path):
    Groq (key 1, then key 2) for fast responses, falling back to the local
    Ollama model if Groq is unset or both keys fail."""
    api_keys = [key for key in (settings.groq_api_key_1, settings.groq_api_key_2) if key]
    if not api_keys:
        return ollama_fallback

    groq = GroqProvider(model_name=settings.groq_model, api_keys=api_keys, reasoning_effort="low")
    return FallbackChatProvider(primary=groq, fallback=ollama_fallback)
