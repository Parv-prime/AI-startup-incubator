from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        protected_namespaces=(),
    )

    app_env: str = "development"
    log_level: str = "INFO"

    model_runtime: str = "ollama"
    model_name: str = "qwen2.5:3b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    model_temperature: float = 0.1
    model_max_tokens: int = 2048

    # Quick chat replies only (ProjectOrchestrator fast path): tries Gemini first
    # (key 1, then key 2), falling back to the local Ollama model above if both
    # Gemini keys fail or are unset. Every other feature (research, financial
    # analysis, viability scoring, tool-calling) stays on `model_runtime` above.
    gemini_api_key_1: str = ""
    gemini_api_key_2: str = ""
    gemini_model: str = "gemini-2.5-flash"
    # Gemini 2.5 models spend part of max_tokens on hidden "thinking" tokens
    # before any visible output, which was truncating structured JSON replies
    # and adding latency. 0 disables thinking for fast, direct answers.
    gemini_thinking_budget: int = 0

    # Primary fast provider for chat + tool-calling: Groq key 1, then key 2,
    # then local Ollama as last resort. Gemini above is currently unused in
    # the chain but left configured in case it's needed again.
    groq_api_key_1: str = ""
    groq_api_key_2: str = ""
    groq_model: str = "openai/gpt-oss-20b"

    max_agent_iterations: int = 6
    agent_timeout_seconds: int = 360
    max_tool_calls_per_run: int = 12

    api_host: str = "127.0.0.1"
    api_port: int = 8080
    api_key: str = "change-me-in-production"
    require_api_key: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "sqlite:///./data/agent.db"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    fast_path_max_tokens: int = 400

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
