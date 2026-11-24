"""JWT issuing (local provider) and verification (local and Supabase providers).

Both providers produce the same `VerifiedIdentity`, so the rest of the application does not care
which provider authenticated the request. Authorization never trusts role claims inside tokens:
the role is always loaded from the BRIDGE database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt

from app.core.config import Settings

SUPABASE_ASYMMETRIC_ALGS = ("RS256", "ES256")


class InvalidTokenError(Exception):
    """Raised for any token that cannot be trusted. The message is safe to log, not to return."""


@dataclass(frozen=True)
class VerifiedIdentity:
    provider: str  # "local" | "supabase"
    subject: str  # local: BRIDGE user id; supabase: Supabase auth user id
    email: str | None


def create_local_access_token(user_id: uuid.UUID, settings: Settings) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = settings.access_token_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "iss": settings.local_jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.local_jwt_secret, algorithm="HS256")
    return token, expires_in


def _verify_local(token: str, settings: Settings) -> VerifiedIdentity:
    try:
        claims = jwt.decode(
            token,
            settings.local_jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.local_jwt_issuer,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(f"local token rejected: {type(exc).__name__}") from exc
    return VerifiedIdentity(provider="local", subject=str(claims["sub"]), email=None)


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=600, timeout=5)


def _verify_supabase(token: str, settings: Settings) -> VerifiedIdentity:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("supabase token header unreadable") from exc

    alg = header.get("alg")
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1" if settings.supabase_url else None
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise InvalidTokenError("HS256 token but SUPABASE_JWT_SECRET is not configured")
        key: object = settings.supabase_jwt_secret
    elif alg in SUPABASE_ASYMMETRIC_ALGS:
        if not settings.supabase_url:
            raise InvalidTokenError("asymmetric token but SUPABASE_URL is not configured")
        try:
            key = (
                _jwks_client(f"{issuer}/.well-known/jwks.json").get_signing_key_from_jwt(token).key
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError("supabase signing key lookup failed") from exc
    else:
        raise InvalidTokenError(f"unsupported token algorithm: {alg!r}")

    options: dict = {"require": ["sub", "exp", "aud"]}
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=settings.supabase_jwt_audience,
            issuer=issuer,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(f"supabase token rejected: {type(exc).__name__}") from exc

    email = claims.get("email")
    return VerifiedIdentity(
        provider="supabase",
        subject=str(claims["sub"]),
        email=email.lower() if isinstance(email, str) else None,
    )


def verify_access_token(token: str, settings: Settings) -> VerifiedIdentity:
    if settings.auth_provider == "supabase":
        return _verify_supabase(token, settings)
    return _verify_local(token, settings)
