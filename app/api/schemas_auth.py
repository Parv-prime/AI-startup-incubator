from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
