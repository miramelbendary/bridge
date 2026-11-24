"""Administrator-editable platform settings with environment defaults."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.platform import PlatformSetting

EDITABLE_KEYS = {
    "ai_provider": str,
    "ai_max_messages_per_session": int,
    "ai_daily_requests_per_user": int,
    "ai_session_budget_usd": float,
    "registration_open": bool,
}


def defaults(settings: Settings) -> dict[str, Any]:
    return {
        "ai_provider": settings.ai_provider,
        "ai_max_messages_per_session": settings.ai_max_messages_per_session,
        "ai_daily_requests_per_user": settings.ai_daily_requests_per_user,
        "ai_session_budget_usd": settings.ai_session_budget_usd,
        "registration_open": True,
    }


def get_all(db: Session, settings: Settings) -> dict[str, Any]:
    values = defaults(settings)
    for row in db.query(PlatformSetting).all():
        if row.key in EDITABLE_KEYS:
            values[row.key] = row.value.get("v", values[row.key])
    return values


def get(db: Session, settings: Settings, key: str) -> Any:
    return get_all(db, settings)[key]


def update(db: Session, settings: Settings, changes: dict[str, Any]) -> dict[str, Any]:
    for key, value in changes.items():
        if key not in EDITABLE_KEYS:
            raise ValueError(f"unknown setting {key!r}")
        typed = EDITABLE_KEYS[key](value)
        if key == "ai_provider":
            if typed not in ("mock", "anthropic"):
                raise ValueError("ai_provider must be 'mock' or 'anthropic'")
            if typed == "anthropic" and not settings.anthropic_api_key:
                raise ValueError("The Anthropic provider is not configured on the server")
        if isinstance(typed, int | float) and not isinstance(typed, bool) and typed <= 0:
            raise ValueError(f"{key} must be positive")
        row = db.get(PlatformSetting, key)
        if row is None:
            db.add(PlatformSetting(key=key, value={"v": typed}))
        else:
            row.value = {"v": typed}
    db.flush()
    return get_all(db, settings)
