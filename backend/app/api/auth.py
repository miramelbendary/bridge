"""Local authentication endpoints (AUTH_PROVIDER=local).

With AUTH_PROVIDER=supabase, registration and login happen in Supabase (from the frontend) and
these two endpoints return 404; the backend only verifies Supabase-issued tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.schemas.auth import AuthConfigResponse, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.security.dependencies import get_settings_dep
from app.security.rate_limit import auth_rate_limit, client_ip
from app.security.tokens import create_local_access_token
from app.services import audit
from app.services.users import (
    EmailAlreadyRegisteredError,
    authenticate_local_user,
    register_local_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _require_local(settings: Settings = Depends(get_settings_dep)) -> Settings:
    if settings.auth_provider != "local":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
    return settings


@router.get("/config", response_model=AuthConfigResponse)
def auth_config(settings: Settings = Depends(get_settings_dep)) -> AuthConfigResponse:
    return AuthConfigResponse(
        provider=settings.auth_provider,
        supabase_url=settings.supabase_url if settings.auth_provider == "supabase" else None,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(_require_local),
) -> TokenResponse:
    from app.services import platform

    if not platform.get(db, settings, "registration_open"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Registration is currently closed")
    try:
        user = register_local_user(
            db, email=body.email, password=body.password, display_name=body.display_name
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="An account with this email already exists"
        ) from None
    audit.record(
        db,
        action="auth.register",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip_address=client_ip(request),
    )
    db.commit()
    token, expires_in = create_local_access_token(user.id, settings)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserRead.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(_require_local),
) -> TokenResponse:
    user = authenticate_local_user(db, email=body.email, password=body.password)
    if user is None:
        # Do not record the attempted email: it may be a mistyped password or personal data.
        audit.record(db, action="auth.login", outcome="failure", ip_address=client_ip(request))
        db.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    audit.record(db, action="auth.login", actor_user_id=user.id, ip_address=client_ip(request))
    db.commit()
    token, expires_in = create_local_access_token(user.id, settings)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserRead.model_validate(user)
    )
