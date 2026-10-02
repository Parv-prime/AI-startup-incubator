from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.core.errors import ModelTimeoutError, ModelUnavailableError
from app.core.ids import new_id
from app.core.logging import get_logger
from app.models.base import ChatMessage, ModelResponse, ModelUsage, ToolCall, ToolSpec

logger = get_logger(__name__)


class OllamaProvider:
    """Local inference via Ollama HTTP API. Replaceable through ModelProvider."""

    runtime = "ollama"

    def __init__(self, *, model_name: str, base_url: str, timeout: float = 120.0):
        self.name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
            return True
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
        payload: dict[str, Any] = {
            "model": self.name,
            "messages": [_to_ollama_message(message) for message in messages],
            "stream": False,
            "options": {},
        }
        if temperature is not None:
            payload["options"]["temperature"] = temperature
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
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

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise ModelTimeoutError("The local model timed out.") from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(
                "The local model runtime is unavailable. Is Ollama running?"
            ) from exc

        message = data.get("message") or {}
        tool_calls = [_parse_tool_call(item) for item in message.get("tool_calls") or []]
        content = message.get("content") or None
        if not tool_calls and content:
            tool_calls = _extract_tool_calls_from_text(content)

        return ModelResponse(
            content=content,
            tool_calls=tool_calls,
            usage=ModelUsage(
                prompt_tokens=data.get("prompt_eval_count"),
                completion_tokens=data.get("eval_count"),
            ),
            finish_reason=data.get("done_reason"),
        )


    async def chat_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self.name,
            "messages": [_to_ollama_message(message) for message in messages],
            "stream": True,
            "options": {},
        }
        if temperature is not None:
            payload["options"]["temperature"] = temperature
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        token = (data.get("message") or {}).get("content")
                        if token:
                            yield token
                        if data.get("done"):
                            break
        except httpx.TimeoutException as exc:
            raise ModelTimeoutError("The local model timed out.") from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(
                "The local model runtime is unavailable. Is Ollama running?"
            ) from exc


def _to_ollama_message(message: ChatMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": message.role, "content": message.content or ""}
    if message.tool_call_id:
        payload["tool_name"] = message.name
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in message.tool_calls
        ]
    return payload


def _parse_tool_call(item: dict[str, Any]) -> ToolCall:
    function = item.get("function") or {}
    arguments = function.get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {"raw": arguments}
    return ToolCall(
        id=item.get("id") or new_id("call"),
        name=function.get("name") or "",
        arguments=arguments if isinstance(arguments, dict) else {},
    )


def _extract_tool_calls_from_text(content: str) -> list[ToolCall]:
    """Fallback when a small model writes a JSON tool call instead of using the API."""
    text = content.strip()
    if "```" in text:
        start = text.find("```")
        rest = text[start + 3 :]
        if rest.startswith("json"):
            rest = rest[4:]
        end = rest.find("```")
        if end != -1:
            text = rest[:end].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, dict):
        return []
    name = parsed.get("name") or parsed.get("tool")
    arguments = parsed.get("arguments") or parsed.get("parameters") or parsed.get("input")
    if not name or not isinstance(arguments, dict):
        return []
    return [ToolCall(id=new_id("call"), name=str(name), arguments=arguments)]
