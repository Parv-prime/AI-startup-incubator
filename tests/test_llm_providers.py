from __future__ import annotations

import json

import httpx
import pytest

from app.agent.engine import AgentEngine
from app.agent.types import AgentRequest
from app.config.settings import Settings
from app.core.errors import (
    ModelAuthError,
    ModelConfigurationError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from app.models.base import ChatMessage, ToolSpec
from app.models.factory import create_model_provider
from app.models.runtimes.cloud import CloudLLMProvider
from app.models.runtimes.fallback import FallbackChatProvider
from app.models.runtimes.ollama import OllamaProvider
from app.tools.registry import ToolRegistry

SECRET = "sk-test-SECRET-should-never-leak"


def _settings(**overrides) -> Settings:
    # _env_file=None: tests must not depend on the developer's local .env
    return Settings(_env_file=None, **overrides)


def _mock(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def _cloud() -> CloudLLMProvider:
    return CloudLLMProvider(base_url="https://llm.example.com/v1/", api_key=SECRET, model_name="test-model")


# --------------------------------------------------------------------- factory --


def test_default_provider_is_local_ollama_qwen():
    provider = create_model_provider(_settings())
    assert isinstance(provider, OllamaProvider)
    assert provider.name == "qwen2.5:3b"
    assert provider.runtime == "ollama"


def test_legacy_env_names_still_select_ollama(monkeypatch):
    monkeypatch.setenv("MODEL_RUNTIME", "ollama")
    monkeypatch.setenv("MODEL_NAME", "qwen2.5:3b")
    settings = _settings()
    assert settings.llm_provider == "ollama"
    assert settings.ollama_model == "qwen2.5:3b"


def test_cloud_provider_without_config_gives_clear_error():
    with pytest.raises(ModelConfigurationError) as info:
        create_model_provider(_settings(llm_provider="cloud"))
    message = info.value.message
    assert "CLOUD_LLM_BASE_URL" in message and "CLOUD_LLM_MODEL" in message and "CLOUD_LLM_API_KEY" in message


def test_cloud_provider_from_config_does_not_need_ollama():
    provider = create_model_provider(
        _settings(
            llm_provider="cloud",
            cloud_llm_base_url="https://llm.example.com/v1",
            cloud_llm_model="some-model",
            cloud_llm_api_key=SECRET,
        )
    )
    assert isinstance(provider, CloudLLMProvider)
    assert provider.name == "some-model"
    assert SECRET not in repr(provider)


def test_unknown_provider_rejected():
    with pytest.raises(ModelConfigurationError):
        create_model_provider(_settings(llm_provider="gemini"))


def test_fallback_only_when_explicitly_configured():
    base = dict(
        llm_provider="cloud",
        cloud_llm_base_url="https://llm.example.com/v1",
        cloud_llm_model="m",
        cloud_llm_api_key=SECRET,
    )
    assert isinstance(create_model_provider(_settings(**base)), CloudLLMProvider)
    assert isinstance(
        create_model_provider(_settings(**base, llm_fallback_provider="ollama")), FallbackChatProvider
    )


# --------------------------------------------------------------- cloud adapter --


@pytest.mark.asyncio
async def test_cloud_chat_success_with_tool_call(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {"name": "calculator", "arguments": '{"expression": "2+2"}'},
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    _mock(monkeypatch, handler)
    response = await _cloud().chat(
        [ChatMessage(role="system", content="sys"), ChatMessage(role="user", content="hi")],
        [ToolSpec(name="calculator", description="calc", parameters={"type": "object", "properties": {}})],
        max_tokens=50,
    )
    assert seen["url"] == "https://llm.example.com/v1/chat/completions"
    assert seen["auth"] == f"Bearer {SECRET}"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert seen["body"]["max_tokens"] == 50
    assert response.tool_calls[0].name == "calculator"
    assert response.tool_calls[0].arguments == {"expression": "2+2"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,error",
    [(401, ModelAuthError), (403, ModelAuthError), (429, ModelRateLimitError), (503, ModelUnavailableError)],
)
async def test_cloud_http_errors_are_clean(monkeypatch, status, error):
    _mock(monkeypatch, lambda request: httpx.Response(status, json={"error": {"message": f"bad key {SECRET}"}}))
    with pytest.raises(error) as info:
        await _cloud().chat([ChatMessage(role="user", content="hi")])
    assert SECRET not in info.value.message
    assert SECRET not in str(info.value)


@pytest.mark.asyncio
async def test_cloud_timeout(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    _mock(monkeypatch, handler)
    with pytest.raises(ModelTimeoutError):
        await _cloud().chat([ChatMessage(role="user", content="hi")])


@pytest.mark.asyncio
async def test_cloud_malformed_response(monkeypatch):
    _mock(monkeypatch, lambda request: httpx.Response(200, json={"unexpected": True}))
    with pytest.raises(ModelResponseError):
        await _cloud().chat([ChatMessage(role="user", content="hi")])


@pytest.mark.asyncio
async def test_cloud_stream(monkeypatch):
    body = (
        'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    _mock(monkeypatch, lambda request: httpx.Response(200, text=body))
    tokens = [t async for t in _cloud().chat_stream([ChatMessage(role="user", content="hi")])]
    assert "".join(tokens) == "Hello"


@pytest.mark.asyncio
async def test_missing_ollama_is_a_clean_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    _mock(monkeypatch, handler)
    provider = OllamaProvider(model_name="qwen2.5:3b", base_url="http://localhost:11434")
    assert await provider.health() is False
    with pytest.raises(ModelUnavailableError):
        await provider.chat([ChatMessage(role="user", content="hi")])


@pytest.mark.asyncio
async def test_agent_reports_provider_failure_without_crashing():
    class DownModel:
        name, runtime = "down", "cloud"

        async def health(self):
            return False

        async def chat(self, *args, **kwargs):
            raise ModelUnavailableError("AI service is temporarily unavailable. Please try again.")

    engine = AgentEngine(model=DownModel(), tools=ToolRegistry(), settings=_settings(agent_timeout_seconds=5))
    result = await engine.run(AgentRequest(input="hi", user_id="u", project_id="p"))
    assert result.status == "failed"
    assert result.output == "AI service is temporarily unavailable. Please try again."
    assert result.error_code == "model_unavailable"


# ------------------------------------------------------------ multi-key pool --


def test_groq_then_gemini_keys_build_ordered_pool():
    from app.models.runtimes.pool import ProviderPool

    provider = create_model_provider(
        _settings(llm_provider="cloud", groq_api_keys="g1, g2,g3", gemini_api_keys="m1,m2,m3")
    )
    assert isinstance(provider, ProviderPool)
    assert [p.label for p in provider.providers] == [
        "groq#1", "groq#2", "groq#3", "gemini#1", "gemini#2", "gemini#3",
    ]
    assert "g1" not in repr(provider)


def test_single_groq_key_is_plain_provider():
    provider = create_model_provider(_settings(llm_provider="cloud", groq_api_key="g1"))
    assert isinstance(provider, CloudLLMProvider)
    assert provider.base_url == "https://api.groq.com/openai/v1"


class _FakeProvider:
    runtime = "cloud"

    def __init__(self, label, error=None):
        self.name = self.label = label
        self.error = error
        self.calls = 0

    async def health(self):
        return self.error is None

    async def chat(self, messages, tools=None, *, temperature=None, max_tokens=None):
        self.calls += 1
        if self.error:
            raise self.error
        from app.models.base import ModelResponse

        return ModelResponse(content=self.label)

    async def chat_stream(self, messages, *, temperature=None, max_tokens=None):
        self.calls += 1
        if self.error:
            raise self.error
        yield self.label


async def test_pool_fails_over_and_skips_cooling_keys():
    from app.models.runtimes.pool import ProviderPool

    now = [0.0]
    limited = _FakeProvider("groq#1", ModelRateLimitError("busy", details={"status": 429, "retry_after": 10}))
    bad_key = _FakeProvider("groq#2", ModelAuthError("no", details={"status": 401}))
    good = _FakeProvider("gemini#1")
    pool = ProviderPool([limited, bad_key, good], clock=lambda: now[0])
    msgs = [ChatMessage(role="user", content="hi")]

    assert (await pool.chat(msgs)).content == "gemini#1"
    assert (await pool.chat(msgs)).content == "gemini#1"
    assert limited.calls == 1 and bad_key.calls == 1  # skipped while cooling down

    now[0] = 11.0  # rate-limit cooldown (Retry-After 10s) expired; auth cooldown has not
    limited.error = None
    assert (await pool.chat(msgs)).content == "groq#1"
    assert bad_key.calls == 1

    assert [t async for t in pool.chat_stream(msgs)] == ["groq#1"]


async def test_pool_raises_last_error_when_all_fail():
    from app.models.runtimes.pool import ProviderPool

    pool = ProviderPool([_FakeProvider("a", ModelTimeoutError("slow")), _FakeProvider("b", ModelRateLimitError("busy"))])
    with pytest.raises(ModelRateLimitError):
        await pool.chat([ChatMessage(role="user", content="hi")])


async def test_retry_after_header_is_parsed(monkeypatch):
    _mock(monkeypatch, lambda request: httpx.Response(429, headers={"retry-after": "7"}, json={}))
    with pytest.raises(ModelRateLimitError) as info:
        await _cloud().chat([ChatMessage(role="user", content="hi")])
    assert info.value.details["retry_after"] == 7.0
