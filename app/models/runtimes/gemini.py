from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.core.errors import ModelTimeoutError, ModelUnavailableError
from app.core.ids import new_id
from app.core.logging import get_logger
from app.models.base import ChatMessage, ModelResponse, ModelUsage, ToolCall, ToolSpec

logger = get_logger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider:
    """Google Gemini via the Generative Language REST API, including function
    (tool) calling so it can drive the same tool-calling agent loop as Ollama.

    Tries each configured API key in order (e.g. a spare key when the first
    hits a rate limit) before giving the caller a chance to fall back to
    another provider entirely.
    """

    runtime = "gemini"

    def __init__(
        self,
        *,
        model_name: str,
        api_keys: list[str],
        timeout: float = 30.0,
        thinking_budget: int | None = 0,
    ):
        if not api_keys:
            raise ValueError("GeminiProvider requires at least one API key.")
        self.name = model_name
        self.api_keys = api_keys
        self.timeout = timeout
        self.thinking_budget = thinking_budget

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{_API_BASE}/{self.name}",
                    params={"key": self.api_keys[0]},
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
            messages,
            tools,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=self.thinking_budget,
        )

        last_exc: Exception | None = None
        for key in self.api_keys:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{_API_BASE}/{self.name}:generateContent",
                        params={"key": key},
                        json=payload,
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    last_exc = ModelUnavailableError(
                        f"Gemini returned {response.status_code} for this key."
                    )
                    continue
                if response.status_code == 400:
                    # A malformed request won't succeed on a different key either.
                    raise ModelUnavailableError(
                        f"Gemini rejected the request: {response.text[:500]}"
                    )
                response.raise_for_status()
                data = response.json()
                return _parse_response(data)
            except httpx.TimeoutException:
                last_exc = ModelTimeoutError("Gemini timed out.")
                continue
            except httpx.HTTPError as exc:
                last_exc = ModelUnavailableError(f"Gemini request failed: {exc}")
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
            messages,
            None,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=self.thinking_budget,
        )

        last_exc: Exception | None = None
        for key in self.api_keys:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{_API_BASE}/{self.name}:streamGenerateContent",
                        params={"key": key, "alt": "sse"},
                        json=payload,
                    ) as response:
                        if response.status_code == 429 or response.status_code >= 500:
                            last_exc = ModelUnavailableError(
                                f"Gemini returned {response.status_code} for this key."
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
                            for candidate in data.get("candidates") or []:
                                for part in (candidate.get("content") or {}).get("parts") or []:
                                    text = part.get("text")
                                    if text:
                                        yield text
                        return
            except httpx.TimeoutException:
                last_exc = ModelTimeoutError("Gemini timed out.")
                continue
            except httpx.HTTPError as exc:
                last_exc = ModelUnavailableError(f"Gemini request failed: {exc}")
                continue

        assert last_exc is not None
        raise last_exc


def _build_payload(
    messages: list[ChatMessage],
    tools: list[ToolSpec] | None,
    *,
    temperature: float | None,
    max_tokens: int | None,
    thinking_budget: int | None = None,
) -> dict[str, Any]:
    system_parts = [m.content for m in messages if m.role == "system" and m.content]
    contents = [_to_gemini_content(m) for m in messages if m.role in ("user", "assistant", "tool")]

    payload: dict[str, Any] = {"contents": contents}
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

    if tools:
        payload["tools"] = [
            {
                "functionDeclarations": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": _sanitize_schema(tool.parameters),
                    }
                    for tool in tools
                ]
            }
        ]

    generation_config: dict[str, Any] = {}
    if temperature is not None:
        generation_config["temperature"] = temperature
    if max_tokens is not None:
        generation_config["maxOutputTokens"] = max_tokens
    if thinking_budget is not None:
        generation_config["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    if generation_config:
        payload["generationConfig"] = generation_config

    return payload


def _to_gemini_content(message: ChatMessage) -> dict[str, Any]:
    if message.role == "tool":
        try:
            response_payload = json.loads(message.content or "{}")
        except json.JSONDecodeError:
            response_payload = {"result": message.content}
        if not isinstance(response_payload, dict):
            response_payload = {"result": response_payload}
        return {
            "role": "function",
            "parts": [
                {
                    "functionResponse": {
                        "name": message.name or "",
                        "response": response_payload,
                    }
                }
            ],
        }

    parts: list[dict[str, Any]] = []
    if message.content:
        parts.append({"text": message.content})
    if message.tool_calls:
        parts.extend(
            {"functionCall": {"name": call.name, "args": call.arguments}}
            for call in message.tool_calls
        )
    if not parts:
        parts.append({"text": ""})

    return {"role": "model" if message.role == "assistant" else "user", "parts": parts}


_SCHEMA_KEEP_KEYS = {
    "type",
    "description",
    "enum",
    "items",
    "properties",
    "required",
    "format",
    "nullable",
}


def _sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip pydantic JSON-Schema fields (title, default, $defs, ...) that
    Gemini's OpenAPI-subset schema validator rejects, keeping only what it
    understands, and upper-casing `type` to match its Type enum."""
    if not isinstance(schema, dict):
        return schema

    cleaned: dict[str, Any] = {}
    for key in _SCHEMA_KEEP_KEYS:
        if key not in schema:
            continue
        value = schema[key]
        if key == "type" and isinstance(value, str):
            cleaned[key] = value.upper()
        elif key == "properties" and isinstance(value, dict):
            cleaned[key] = {name: _sanitize_schema(prop) for name, prop in value.items()}
        elif key == "items" and isinstance(value, dict):
            cleaned[key] = _sanitize_schema(value)
        else:
            cleaned[key] = value

    if not cleaned.get("properties"):
        cleaned.setdefault("type", "OBJECT")
        cleaned.setdefault("properties", {})
    return cleaned


def _parse_response(data: dict[str, Any]) -> ModelResponse:
    candidates = data.get("candidates") or []
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    finish_reason = None
    if candidates:
        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        for part in (candidate.get("content") or {}).get("parts") or []:
            if "text" in part and part["text"]:
                text_parts.append(part["text"])
            function_call = part.get("functionCall")
            if function_call:
                args = function_call.get("args") or {}
                tool_calls.append(
                    ToolCall(
                        id=new_id("call"),
                        name=function_call.get("name") or "",
                        arguments=args if isinstance(args, dict) else {},
                    )
                )

    usage = data.get("usageMetadata") or {}
    return ModelResponse(
        content="".join(text_parts) or None,
        tool_calls=tool_calls,
        usage=ModelUsage(
            prompt_tokens=usage.get("promptTokenCount"),
            completion_tokens=usage.get("candidatesTokenCount"),
        ),
        finish_reason=finish_reason,
    )
