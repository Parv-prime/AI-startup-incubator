from __future__ import annotations

from app.models.base import ModelProvider
from app.models.structured import generate_json
from app.startup.profile import ProfileUpdate

SYSTEM_PROMPT = """You extract structured startup facts from a founder's message.

Only extract facts that are explicitly stated or very strongly implied in THIS message.
Leave a field as null if it is not mentioned. Do not guess or invent values.

Respond with ONLY a JSON object with exactly these keys (use null for anything unknown):
{
  "startup_name": string or null,
  "industry": string or null,
  "problem": string or null,
  "solution": string or null,
  "target_customer": string or null,
  "geography": string or null,
  "business_model": string or null,
  "startup_stage": string or null,
  "budget": string or null,
  "goals": string or null
}
"""


async def extract_profile_updates(model: ModelProvider, user_input: str) -> ProfileUpdate:
    parsed = await generate_json(
        model,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_input,
        temperature=0.0,
        max_tokens=400,
    )
    if parsed is None:
        return ProfileUpdate()

    fields = {}
    for key in ProfileUpdate.model_fields:
        value = parsed.get(key)
        fields[key] = str(value).strip() if isinstance(value, str) and value.strip() else None
    return ProfileUpdate.model_validate(fields)
