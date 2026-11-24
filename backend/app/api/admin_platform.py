"""Administrator controls beyond user roles: platform and AI settings, usage monitoring,
account activation, specializations and scenario publication."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.common import not_found
from app.core.config import Settings
from app.db.session import get_db
from app.models.platform import AIUsageLog
from app.models.simulation import SimulationSession
from app.models.specialization import Specialization
from app.models.user import User
from app.schemas.common import StrictModel
from app.security.dependencies import get_settings_dep, require_permission
from app.security.permissions import Permission
from app.security.rate_limit import client_ip
from app.services import audit, platform
from app.services import scenarios as scenario_service

router = APIRouter(prefix="/admin", tags=["admin"])


class SettingsPatch(StrictModel):
    changes: dict[str, Any]


class ActiveIn(StrictModel):
    is_active: bool


class SpecializationIn(StrictModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,49}$")
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)


class SpecializationPatch(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class ScenarioStatusIn(StrictModel):
    status: Literal["draft", "published", "archived"]


@router.get("/settings")
def get_settings_route(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.PLATFORM_MANAGE)),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    return {
        "values": platform.get_all(db, settings),
        "anthropic_configured": bool(settings.anthropic_api_key),
        "ai_model": settings.ai_model,
    }


@router.patch("/settings")
def patch_settings(
    body: SettingsPatch,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.PLATFORM_MANAGE)),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    try:
        values = platform.update(db, settings, body.changes)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, detail=str(exc)) from None
    audit.record(
        db,
        action="admin.settings_changed",
        actor_user_id=user.id,
        ip_address=client_ip(request),
        details={"changes": body.changes},
    )
    db.commit()
    return {
        "values": values,
        "anthropic_configured": bool(settings.anthropic_api_key),
        "ai_model": settings.ai_model,
    }


@router.get("/usage")
def usage(
    days: int = 7,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.USAGE_READ)),
) -> dict:
    since = datetime.now(UTC) - timedelta(days=max(1, min(days, 90)))
    rows = db.execute(
        select(
            AIUsageLog.provider,
            AIUsageLog.purpose,
            func.count(),
            func.sum(AIUsageLog.input_tokens),
            func.sum(AIUsageLog.output_tokens),
            func.sum(AIUsageLog.estimated_cost_usd),
            func.avg(AIUsageLog.latency_ms),
            func.sum(case((AIUsageLog.success.is_(False), 1), else_=0)),
            func.sum(case((AIUsageLog.used_fallback.is_(True), 1), else_=0)),
        )
        .where(AIUsageLog.created_at >= since)
        .group_by(AIUsageLog.provider, AIUsageLog.purpose)
    ).all()
    sessions = db.scalar(
        select(func.count())
        .select_from(SimulationSession)
        .where(SimulationSession.started_at >= since)
    )
    completed = db.scalar(
        select(func.count())
        .select_from(SimulationSession)
        .where(SimulationSession.started_at >= since, SimulationSession.status == "completed")
    )
    recent_errors = db.scalars(
        select(AIUsageLog)
        .where(AIUsageLog.error.is_not(None))
        .order_by(AIUsageLog.created_at.desc())
        .limit(20)
    )
    return {
        "days": days,
        "sessions_started": sessions or 0,
        "sessions_completed": completed or 0,
        "completion_rate": round(100 * (completed or 0) / sessions, 1) if sessions else None,
        "breakdown": [
            {
                "provider": r[0],
                "purpose": r[1],
                "calls": r[2],
                "input_tokens": int(r[3] or 0),
                "output_tokens": int(r[4] or 0),
                "estimated_cost_usd": round(float(r[5] or 0), 4),
                "avg_latency_ms": round(float(r[6] or 0)),
                "failures": int(r[7] or 0),
                "fallbacks": int(r[8] or 0),
            }
            for r in rows
        ],
        "recent_errors": [
            {
                "at": e.created_at.isoformat(),
                "provider": e.provider,
                "purpose": e.purpose,
                "error": e.error,
            }
            for e in recent_errors
        ],
    }


@router.patch("/users/{user_id}/active")
def set_active(
    user_id: uuid.UUID,
    body: ActiveIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission(Permission.USERS_MANAGE_ROLES)),
) -> dict:
    target = db.get(User, user_id)
    if target is None:
        raise not_found("User not found")
    if target.id == actor.id and not body.is_active:
        raise HTTPException(409, detail="You cannot deactivate your own account")
    target.is_active = body.is_active
    audit.record(
        db,
        action="admin.user.active_changed",
        actor_user_id=actor.id,
        target_type="user",
        target_id=str(target.id),
        ip_address=client_ip(request),
        details={"is_active": body.is_active},
    )
    db.commit()
    return {"id": str(target.id), "is_active": target.is_active}


@router.get("/specializations")
def all_specializations(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.SPECIALIZATIONS_MANAGE)),
) -> list[dict]:
    return [
        {
            "id": str(s.id),
            "code": s.code,
            "name": s.name,
            "description": s.description,
            "is_active": s.is_active,
        }
        for s in db.scalars(select(Specialization).order_by(Specialization.name))
    ]


@router.post("/specializations", status_code=201)
def create_specialization(
    body: SpecializationIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.SPECIALIZATIONS_MANAGE)),
) -> dict:
    if db.scalar(select(Specialization).where(Specialization.code == body.code)):
        raise HTTPException(409, detail="A specialization with this code exists")
    spec = Specialization(
        code=body.code, name=body.name, description=body.description, is_active=True
    )
    db.add(spec)
    audit.record(
        db,
        action="admin.specialization_created",
        actor_user_id=user.id,
        ip_address=client_ip(request),
        details={"code": body.code},
    )
    db.commit()
    return {"id": str(spec.id), "code": spec.code}


@router.patch("/specializations/{spec_id}")
def update_specialization(
    spec_id: uuid.UUID,
    body: SpecializationPatch,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.SPECIALIZATIONS_MANAGE)),
) -> dict:
    spec = db.get(Specialization, spec_id)
    if spec is None:
        raise not_found("Specialization not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(spec, field, value)
    db.commit()
    return {"id": str(spec.id), "code": spec.code, "is_active": spec.is_active}


@router.get("/scenarios")
def all_scenarios(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.SCENARIOS_PUBLISH)),
) -> list[dict]:
    return [
        scenario_service.summary(s)
        for s in scenario_service.list_scenarios(db, include_unpublished=True)
    ]


@router.post("/scenarios/{slug}/status")
def set_scenario_status(
    slug: str,
    body: ScenarioStatusIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.SCENARIOS_PUBLISH)),
) -> dict:
    scenario = scenario_service.get_by_slug(db, slug)
    if scenario is None:
        raise not_found("Scenario not found")
    scenario.status = body.status
    audit.record(
        db,
        action="admin.scenario_status",
        actor_user_id=user.id,
        target_type="scenario",
        target_id=slug,
        ip_address=client_ip(request),
        details={"status": body.status},
    )
    db.commit()
    return {"slug": slug, "status": scenario.status}
