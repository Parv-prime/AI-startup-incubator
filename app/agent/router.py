"""Classifies a user message as FAST (direct answer from memory/profile/recent
chat, no tools) or AGENT (needs the tool-calling loop: research, calculations,
viability). Deliberately a cheap keyword heuristic, not an extra LLM
call — see section 67 (minimize LLM calls) of the product spec.

Report requests are intentionally NOT routed to the agent path — there is no
report tool available in chat, so "report"/"summary" asks stay on the fast
conversational path, which tells the user to use the Report page's button.
"""

from __future__ import annotations

import re

_AGENT_KEYWORDS = (
    "research",
    "competitor",
    "competitors",
    "market",
    "financial",
    "finance",
    "break-even",
    "break even",
    "budget",
    "revenue",
    "cost",
    "pricing",
    "price",
    "viability",
    "viable",
    "score",
    "roadmap",
    "calculate",
    "calculation",
    "projection",
    "forecast",
    "remember that",
    "we decided",
    "our decision",
)

_NUMBER_RE = re.compile(r"\d")


def needs_agent_path(user_input: str) -> bool:
    text = user_input.lower()
    if any(keyword in text for keyword in _AGENT_KEYWORDS):
        return True
    # A message with numbers in it is often asking for a calculation.
    if _NUMBER_RE.search(text) and any(op in text for op in ("$", "%", "per month", "per year")):
        return True
    return False
