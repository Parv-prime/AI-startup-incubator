from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        protected_namespaces=(),
        populate_by_name=True,
    )

    app_env: str = "development"
    log_level: str = "INFO"

    # --- LLM provider -------------------------------------------------------
    # Chosen by the deployment environment, never by who is logged in:
    #   "ollama" → local Ollama (development)
    #   "cloud"  → generic OpenAI-compatible endpoint (production)
    # MODEL_RUNTIME / MODEL_NAME are the legacy names and still work.
    llm_provider: str = Field(
        default="ollama", validation_alias=AliasChoices("llm_provider", "model_runtime")
    )
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = Field(
        default="qwen2.5:3b", validation_alias=AliasChoices("ollama_model", "model_name")
    )

    cloud_llm_api_key: str = ""
    cloud_llm_base_url: str = ""
    cloud_llm_model: str = ""
    cloud_llm_timeout_seconds: float = 60.0
    # Optional OpenAI-style "reasoning_effort" for reasoning models that spend
    # max_tokens on hidden reasoning; leave empty for providers that reject it.
    cloud_llm_reasoning_effort: str = ""

    # Multi-key failover for LLM_PROVIDER=cloud. Comma-separated keys, tried in
    # order: CLOUD_LLM_* (if fully set) → each Groq key → each Gemini key. A key
    # that is rate-limited or rejected is skipped until its cooldown expires.
    groq_api_keys: str = Field(default="", validation_alias=AliasChoices("groq_api_keys", "groq_api_key"))
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_keys: str = Field(
        default="", validation_alias=AliasChoices("gemini_api_keys", "gemini_api_key")
    )
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    gemini_model: str = "gemini-2.5-flash"

    # Optional explicit fallback when the primary provider fails. Only "ollama"
    # is supported, and only ever used when set — a deployed server never calls
    # localhost Ollama unless this is configured.
    llm_fallback_provider: str = ""

    model_temperature: float = 0.1
    model_max_tokens: int = 2048
    fast_path_max_tokens: int = 400
    # How many recent chat messages are sent back to the model as context.
    chat_history_limit: int = 16
    # Per-user chat requests allowed per minute (0 disables the throttle).
    chat_rate_limit_per_minute: int = 0

    # --- Agent --------------------------------------------------------------
    max_agent_iterations: int = 6
    agent_timeout_seconds: int = 360
    max_tool_calls_per_run: int = 12

    # --- Live research ------------------------------------------------------
    research_provider: str = "exa"
    research_fallback_providers: str = "tavily,duckduckgo"
    tavily_api_key: str = ""
    tavily_search_depth: str = "basic"
    exa_api_key: str = ""
    jina_api_key: str = ""
    jina_reader_enabled: bool = True
    research_cache_enabled: bool = True
    research_cache_ttl_seconds: int = 3600
    research_max_results: int = 5
    research_max_fetched_pages: int = 3
    research_timeout_seconds: float = 15.0
    research_fetch_timeout_seconds: float = 15.0
    research_max_chars_per_source: int = 1500

    # --- API ----------------------------------------------------------------
    api_host: str = "127.0.0.1"
    # Render (and most PaaS hosts) inject PORT; API_PORT is the local name.
    api_port: int = Field(default=8080, validation_alias=AliasChoices("port", "api_port"))
    api_key: str = _INSECURE_SECRET
    require_api_key: bool = False
    cors_origins: str = "http://localhost:5175,http://127.0.0.1:5175"

    database_url: str = "sqlite:///./data/agent.db"

    jwt_secret_key: str = _INSECURE_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def research_provider_order(self) -> list[str]:
        names = [self.research_provider, *self.research_fallback_providers.split(",")]
        ordered: list[str] = []
        for name in names:
            name = name.strip().lower()
            if name and name not in ordered:
                ordered.append(name)
        return ordered

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local", "test"}

    def production_problems(self) -> list[str]:
        """Configuration that is acceptable locally but unsafe once deployed."""
        problems: list[str] = []
        if self.is_development:
            return problems
        if not self.jwt_secret_key or self.jwt_secret_key.startswith("change-me"):
            problems.append("JWT_SECRET_KEY must be set to a long random value in production.")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
