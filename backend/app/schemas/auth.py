from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import StrictModel
from app.schemas.user import UserRead


class RegisterRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 - not a secret
    expires_in: int
    user: UserRead


class AuthConfigResponse(BaseModel):
    provider: Literal["local", "supabase"]
    supabase_url: str | None = None
