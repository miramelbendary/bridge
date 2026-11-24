"""Application settings, loaded from environment variables (and an optional .env file).

Secrets (JWT secrets, database passwords, future AI provider keys) are only ever read from the
environment. They are never stored in the database or returned by the API.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder only; rejected in production by the validator below.
INSECURE_DEV_SECRET = "dev-only-insecure-secret-change-me-0000000000"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "BRIDGE API"
    api_prefix: str = "/api/v1"

    # Database. PostgreSQL is the supported target; SQLite is accepted for local tests only.
    database_url: str = "postgresql+psycopg://bridge:bridge@localhost:5432/bridge"
    database_echo: bool = False

    # Authentication. "local" = BRIDGE issues its own JWTs (development/demo without Supabase).
    # "supabase" = Supabase Auth issues JWTs and the backend verifies them.
    auth_provider: Literal["local", "supabase"] = "local"
    local_jwt_secret: str = INSECURE_DEV_SECRET
    local_jwt_issuer: str = "bridge-local"
    jwt_audience: str = "bridge-api"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=24 * 60)

    supabase_url: str | None = None
    supabase_jwt_secret: str | None = None  # legacy HS256 projects
    supabase_jwt_audience: str = "authenticated"

    # HTTP
    cors_origins: list[str] = ["http://localhost:3000"]

    # Rate limiting for authentication endpoints (per client IP, per endpoint).
    auth_rate_limit_attempts: int = Field(default=10, ge=1)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _validate_security(self) -> Settings:
        if self.auth_provider == "local":
            if len(self.local_jwt_secret) < 32:
                raise ValueError("LOCAL_JWT_SECRET must be at least 32 characters long")
            if self.environment == "production" and self.local_jwt_secret == INSECURE_DEV_SECRET:
                raise ValueError("LOCAL_JWT_SECRET must be changed in production")
        if self.auth_provider == "supabase" and not (self.supabase_url or self.supabase_jwt_secret):
            raise ValueError(
                "AUTH_PROVIDER=supabase requires SUPABASE_URL (JWKS) or SUPABASE_JWT_SECRET"
            )
        if self.environment == "production" and self.database_url.startswith("sqlite"):
            raise ValueError("SQLite is not supported in production; use PostgreSQL")
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not allowed (credentials are used)")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
