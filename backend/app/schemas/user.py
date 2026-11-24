from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.user import Role
from app.schemas.common import ORMModel, StrictModel


class SpecializationRead(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str


class ProfileRead(ORMModel):
    display_name: str
    specialization: SpecializationRead | None = None


class UserRead(ORMModel):
    id: uuid.UUID
    email: str
    role: Role
    is_active: bool
    created_at: datetime
    profile: ProfileRead | None = None


class MeResponse(UserRead):
    permissions: list[str]


class ProfileUpdate(StrictModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    specialization_code: str | None = Field(default=None, min_length=1, max_length=50)


class RoleUpdate(StrictModel):
    role: Role


class AuditLogRead(ORMModel):
    id: uuid.UUID
    occurred_at: datetime
    actor_user_id: uuid.UUID | None
    action: str
    outcome: str
    target_type: str | None
    target_id: str | None
    ip_address: str | None
    details: dict
