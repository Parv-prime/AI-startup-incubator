"""Helper for getting structured JSON out of a small local LLM.

Used by tools that need qualitative synthesis (market/competitor research,
profile extraction) without trusting the model to control control-flow.
The caller always has a safe fallback if parsing fails.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.models.base import ChatMessage, ModelProvider


async def generate_json(
    model: ModelProvider,
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 700,
) -> dict[str, Any] | None:
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]
    for _ in range(2):  # one retry on malformed output
        response = await model.chat(messages, temperature=temperature, max_tokens=max_tokens)
        parsed = _extract_json(response.content or "")
        if parsed is not None:
            return parsed
        messages.append(
            ChatMessage(
                role="user",
                content="That was not valid JSON. Reply with ONLY a single valid JSON object.",
            )
        )
    return None


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            parsed = json.loads(fence_match.group(1))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

    return None
