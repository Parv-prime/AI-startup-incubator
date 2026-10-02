from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.database.models import User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


def validate_signup_input(name: str, email: str, password: str) -> None:
    if not name or not name.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name is required.")
    if not email or not EMAIL_RE.match(email):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A valid email address is required.")
    if not password or len(password) < 8:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Password must be at least 8 characters long."
        )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(settings: Settings, user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(settings: Settings, token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Session expired. Please log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid authentication token.") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Invalid authentication token.")
    return user_id


def verify_api_key(settings: Settings, x_api_key: str | None) -> None:
    if not settings.require_api_key:
        return
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key.")


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing or invalid Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    settings: Settings = request.app.state.settings
    user_id = decode_access_token(settings, token)

    db = request.app.state.db
    async with db.session() as session:  # type: AsyncSession
        user = await session.get(User, user_id)
        if user is None:
            raise AuthError("User no longer exists.")
        return user
