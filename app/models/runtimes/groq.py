from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.core.errors import ModelTimeoutError, ModelUnavailableError
from app.core.ids import new_id
from app.core.logging import get_logger
from app.models.base import ChatMessage, ModelResponse, ModelUsage, ToolCall, ToolSpec

logger = get_logger(__name__)

_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    """Groq's OpenAI-compatible chat completions API.

    Tries each configured API key in order (e.g. a spare key when the first
    hits a rate limit) before giving the caller a chance to fall back to
    another provider entirely.
    """

    runtime = "groq"

    def __init__(
        self,
        *,
        model_name: str,
        api_keys: list[str],
        timeout: float = 30.0,
        reasoning_effort: str | None = "low",
    ):
        if not api_keys:
            raise ValueError("GroqProvider requires at least one API key.")
        self.name = model_name
        self.api_keys = api_keys
        self.timeout = timeout
        # gpt-oss models spend part of max_tokens on a hidden "reasoning"
        # field before any visible content, which was truncating replies to
        # empty strings. "low" keeps that short so tokens go to the answer.
        self.reasoning_effort = reasoning_effort

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {self.api_keys[0]}"},
                )
            return response.status_code < 500
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
        payload = _build_payload(
            self.name,
            messages,
            tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            reasoning_effort=self.reasoning_effort,
        )

        last_exc: Exception | None = None
        for key in self.api_keys:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        _API_URL,
                        headers={"Authorization": f"Bearer {key}"},
                        json=payload,
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    last_exc = ModelUnavailableError(
                        f"Groq returned {response.status_code} for this key."
                    )
                    continue
                if response.status_code == 400:
                    raise ModelUnavailableError(
                        f"Groq rejected the request: {response.text[:500]}"
                    )
                response.raise_for_status()
                return _parse_response(response.json())
            except httpx.TimeoutException:
                last_exc = ModelTimeoutError("Groq timed out.")
                continue
            except httpx.HTTPError as exc:
                last_exc = ModelUnavailableError(f"Groq request failed: {exc}")
                continue

        assert last_exc is not None
        raise last_exc

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        payload = _build_payload(
            self.name,
            messages,
            None,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            reasoning_effort=self.reasoning_effort,
        )

        last_exc: Exception | None = None
        for key in self.api_keys:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST",
                        _API_URL,
                        headers={"Authorization": f"Bearer {key}"},
                        json=payload,
                    ) as response:
                        if response.status_code == 429 or response.status_code >= 500:
                            last_exc = ModelUnavailableError(
                                f"Groq returned {response.status_code} for this key."
                            )
                            continue
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            chunk = line[len("data:") :].strip()
                            if not chunk or chunk == "[DONE]":
                                continue
                            data = json.loads(chunk)
                            for choice in data.get("choices") or []:
                                text = (choice.get("delta") or {}).get("content")
                                if text:
                                    yield text
                        return
            except httpx.TimeoutException:
                last_exc = ModelTimeoutError("Groq timed out.")
                continue
            except httpx.HTTPError as exc:
                last_exc = ModelUnavailableError(f"Groq request failed: {exc}")
                continue

        assert last_exc is not None
        raise last_exc


def _build_payload(
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
    if reasoning_effort is not None:
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


def _parse_response(data: dict[str, Any]) -> ModelResponse:
    choices = data.get("choices") or []
    content = None
    tool_calls: list[ToolCall] = []
    finish_reason = None
    if choices:
        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        message = choice.get("message") or {}
        content = message.get("content") or None
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
        finish_reason=finish_reason,
    )
