"""Optional per-user throttle for chat requests (protects free-tier LLM/search quotas).

In-memory and per-process: good enough for a single small instance (e.g. one
Render free web service). Disabled when CHAT_RATE_LIMIT_PER_MINUTE=0.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from app.database.models import User
from app.security.auth import get_current_user

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(user_id: str, limit: int, *, now: float | None = None) -> bool:
    """Record a request; return False when the user is over `limit` per minute."""
    if limit <= 0:
        return True
    now = time.monotonic() if now is None else now
    hits = _hits[user_id]
    while hits and now - hits[0] > _WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= limit:
        return False
    hits.append(now)
    return True


async def enforce_chat_rate_limit(
    request: Request, current_user: User = Depends(get_current_user)
) -> None:
    limit = request.app.state.settings.chat_rate_limit_per_minute
    if not check_rate_limit(current_user.id, limit):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "You're sending messages too quickly. Please wait a moment and try again.",
        )
