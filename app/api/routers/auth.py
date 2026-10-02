from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.schemas_auth import AuthResponse, LoginRequest, SignupRequest, UserResponse
from app.database.models import User
from app.projects.store import create_user, get_user_by_email
from app.security.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    validate_signup_input,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    validate_signup_input(payload.name, payload.email, payload.password)
    user = await create_user(
        session,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    token = create_access_token(request.app.state.settings, user.id)
    return AuthResponse(user=UserResponse.model_validate(user, from_attributes=True), access_token=token)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user = await get_user_by_email(session, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    token = create_access_token(request.app.state.settings, user.id)
    return AuthResponse(user=UserResponse.model_validate(user, from_attributes=True), access_token=token)


@router.post("/logout")
async def logout() -> dict:
    # Stateless JWT: the client discards the token. Nothing to invalidate server-side yet.
    return {"success": True}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user, from_attributes=True)
