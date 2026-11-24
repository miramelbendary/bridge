"""FastAPI dependencies for authentication and authorization.

Every protected route depends on `get_current_user` or `require_permission(...)`. Access control is
enforced here, on the backend; the frontend hiding a button is never a security control.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_db
from app.models.user import User
from app.security.permissions import Permission, has_permission
from app.security.tokens import InvalidTokenError, verify_access_token
from app.services import audit
from app.services.users import UserProvisioningError, get_or_provision_external_user

logger = logging.getLogger("bridge.auth")

_bearer = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _UNAUTHENTICATED
    try:
        identity = verify_access_token(credentials.credentials, settings)
    except InvalidTokenError as exc:
        logger.info("Rejected token: %s", exc)
        raise _UNAUTHENTICATED from None

    user: User | None
    if identity.provider == "local":
        try:
            user_id = uuid.UUID(identity.subject)
        except ValueError:
            raise _UNAUTHENTICATED from None
        user = db.get(User, user_id)
        if user is not None and user.auth_provider != "local":
            user = None
    else:
        try:
            user = get_or_provision_external_user(db, identity)
        except UserProvisioningError as exc:
            logger.warning("External user provisioning refused: %s", exc)
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail="Account cannot be used"
            ) from None

    if user is None or not user.is_active:
        raise _UNAUTHENTICATED
    request.state.user_id = user.id
    return user


def require_permission(permission: Permission) -> Callable[..., User]:
    def _checker(
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not has_permission(user.role, permission):
            audit.record(
                db,
                action="authz.denied",
                outcome="denied",
                actor_user_id=user.id,
                ip_address=request.client.host if request.client else None,
                details={"permission": permission.value, "path": request.url.path},
            )
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _checker
