from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.user import AuditLogRead, RoleUpdate, UserRead
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.rate_limit import client_ip
from app.services import audit
from app.services.users import RoleChangeError, change_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.USERS_READ_ALL)),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[User]:
    return list(
        db.scalars(
            select(User).order_by(User.created_at, User.id).limit(limit).offset(offset)
        ).unique()
    )


@router.patch("/users/{user_id}/role", response_model=UserRead)
def update_user_role(
    user_id: uuid.UUID,
    body: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.USERS_MANAGE_ROLES)),
) -> User:
    target = db.get(User, user_id)
    previous_role = target.role if target else None
    try:
        updated = change_role(db, actor=actor, target_id=user_id, new_role=body.role)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found") from None
    except RoleChangeError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None
    audit.record(
        db,
        action="admin.user.role_changed",
        actor_user_id=actor.id,
        target_type="user",
        target_id=str(user_id),
        ip_address=client_ip(request),
        details={"from": previous_role, "to": body.role.value},
    )
    db.commit()
    db.refresh(updated)
    return updated


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.AUDIT_READ)),
    action: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.occurred_at.desc(), AuditLog.id).limit(limit)
    if action:
        query = query.where(AuditLog.action == action)
    return list(db.scalars(query))
