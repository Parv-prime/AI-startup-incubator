from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.core.errors import (
    ModelAuthError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from app.core.ids import new_id
from app.core.logging import get_logger
from app.models.base import ChatMessage, ModelResponse, ModelUsage, ToolCall, ToolSpec

logger = get_logger(__name__)

# Shown to end users. Provider details (status codes, bodies) go to the logs only.
UNAVAILABLE_MESSAGE = "AI service is temporarily unavailable. Please try again."
RATE_LIMIT_MESSAGE = "AI service is busy right now (rate limit reached). Please try again shortly."
TIMEOUT_MESSAGE = "AI service took too long to respond. Please try again."


class CloudLLMProvider:
    """Generic cloud LLM behind the OpenAI-compatible Chat Completions format.

    Not tied to any vendor: point CLOUD_LLM_BASE_URL at any endpoint that serves
    `POST {base_url}/chat/completions` (with optional function/tool calling) and
    set CLOUD_LLM_MODEL / CLOUD_LLM_API_KEY. The API key is only ever sent in the
    Authorization header and is never logged or included in error messages.
    """

    runtime = "cloud"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout: float = 60.0,
        reasoning_effort: str | None = None,
        label: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.name = model_name
        # Key-free identifier for logs, e.g. "groq#2" when several keys are pooled.
        self.label = label or model_name
        self._api_key = api_key
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort or None

    def __repr__(self) -> str:  # never show the key
        return f"CloudLLMProvider(label={self.label!r}, base_url={self.base_url!r}, model={self.name!r})"

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/models", headers=self._headers)
            return response.status_code < 500 and response.status_code not in (401, 403)
        except httpx.HTTPError:
            return False

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ModelResponse:
        payload = build_payload(
            self.name,
            messages,
            tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            reasoning_effort=self.reasoning_effort,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=self._headers, json=payload
                )
        except httpx.TimeoutException as exc:
            logger.warning("cloud_llm_timeout", extra={"model": self.name})
            raise ModelTimeoutError(TIMEOUT_MESSAGE) from exc
        except httpx.HTTPError as exc:
            logger.warning("cloud_llm_network_error", extra={"model": self.name, "error": type(exc).__name__})
            raise ModelUnavailableError(UNAVAILABLE_MESSAGE) from exc

        _raise_for_status(response, self.name)
        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("cloud_llm_non_json_response", extra={"model": self.name})
            raise ModelResponseError(UNAVAILABLE_MESSAGE) from exc
        return parse_response(data)

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        payload = build_payload(
            self.name,
            messages,
            None,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            reasoning_effort=self.reasoning_effort,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/chat/completions", headers=self._headers, json=payload
                ) as response:
                    if response.status_code >= 400:
                        await response.aread()
                        _raise_for_status(response, self.name)
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        chunk = line[len("data:") :].strip()
                        if not chunk or chunk == "[DONE]":
                            continue
                        try:
                            data = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
                        for choice in data.get("choices") or []:
                            text = (choice.get("delta") or {}).get("content")
                            if text:
                                yield text
        except httpx.TimeoutException as exc:
            logger.warning("cloud_llm_timeout", extra={"model": self.name})
            raise ModelTimeoutError(TIMEOUT_MESSAGE) from exc
        except httpx.HTTPError as exc:
            logger.warning("cloud_llm_network_error", extra={"model": self.name, "error": type(exc).__name__})
            raise ModelUnavailableError(UNAVAILABLE_MESSAGE) from exc


def _raise_for_status(response: httpx.Response, model: str) -> None:
    status = response.status_code
    if status < 400:
        return
    # Log a short, key-free excerpt of the provider's error body for diagnosis.
    excerpt = response.text[:300] if response.text else ""
    logger.warning("cloud_llm_http_error", extra={"model": model, "status": status, "body": excerpt})
    if status in (401, 403):
        raise ModelAuthError(UNAVAILABLE_MESSAGE, details={"status": status})
    if status == 429:
        details: dict = {"status": status}
        retry_after = _retry_after_seconds(response)
        if retry_after is not None:
            details["retry_after"] = retry_after
        raise ModelRateLimitError(RATE_LIMIT_MESSAGE, details=details)
    raise ModelUnavailableError(UNAVAILABLE_MESSAGE, details={"status": status})


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """Seconds from a numeric Retry-After header (Groq sends one; others may not)."""
    try:
        value = float(response.headers.get("retry-after", ""))
    except ValueError:
        return None
    return value if value >= 0 else None


def build_payload(
    model_name: str,
    messages: list[ChatMessage],
    tools: list[ToolSpec] | None,
    *,
    temperature: float | None,
    max_tokens: int | None,
    stream: bool,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [_to_openai_message(m) for m in messages],
        "stream": stream,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    if tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]
    return payload


def _to_openai_message(message: ChatMessage) -> dict[str, Any]:
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id or "",
            "content": message.content or "",
        }

    payload: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    return payload


def parse_response(data: Any) -> ModelResponse:
    if not isinstance(data, dict) or not isinstance(data.get("choices"), list) or not data["choices"]:
        logger.warning("cloud_llm_malformed_response")
        raise ModelResponseError(UNAVAILABLE_MESSAGE)

    choice = data["choices"][0] if isinstance(data["choices"][0], dict) else {}
    message = choice.get("message") or {}
    content = message.get("content") or None
    tool_calls: list[ToolCall] = []
    for item in message.get("tool_calls") or []:
        function = item.get("function") or {}
        arguments = function.get("arguments") or "{}"
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"raw": arguments}
        tool_calls.append(
            ToolCall(
                id=item.get("id") or new_id("call"),
                name=function.get("name") or "",
                arguments=arguments if isinstance(arguments, dict) else {},
            )
        )

    usage = data.get("usage") or {}
    return ModelResponse(
        content=content,
        tool_calls=tool_calls,
        usage=ModelUsage(
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        ),
        finish_reason=choice.get("finish_reason"),
    )
