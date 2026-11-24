"""Audit logging. Callers add the entry to the current transaction and commit with their change,
so an audited action and its audit record succeed or fail together."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog

_FORBIDDEN_DETAIL_KEYS = {"password", "password_hash", "token", "access_token", "secret"}


def record(
    db: Session,
    *,
    action: str,
    outcome: str = "success",
    actor_user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    safe_details = {
        k: v for k, v in (details or {}).items() if k.lower() not in _FORBIDDEN_DETAIL_KEYS
    }
    entry = AuditLog(
        action=action,
        outcome=outcome,
        actor_user_id=actor_user_id,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        details=safe_details,
    )
    db.add(entry)
    return entry
