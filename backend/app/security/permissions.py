"""Role-based permissions.

Permissions are defined in code (reviewed, versioned, tested) rather than in database tables.
Each later phase adds the permissions it needs here. Ownership checks (e.g. "a student may only
read their own assessments") are enforced in services, on top of these coarse permissions.
"""

from __future__ import annotations

import enum

from app.models.user import Role


class Permission(enum.StrEnum):
    PROFILE_READ_OWN = "profile:read_own"
    PROFILE_UPDATE_OWN = "profile:update_own"
    SPECIALIZATIONS_READ = "specializations:read"
    USERS_READ_ALL = "users:read_all"
    USERS_MANAGE_ROLES = "users:manage_roles"
    AUDIT_READ = "audit:read"


_COMMON = {
    Permission.PROFILE_READ_OWN,
    Permission.PROFILE_UPDATE_OWN,
    Permission.SPECIALIZATIONS_READ,
}

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.STUDENT: frozenset(_COMMON),
    # Professor permissions (scenario editing, rubric editing, reviewing authorized students)
    # arrive with the features in Phases 5 and 9. Professors must NOT get users:read_all.
    Role.PROFESSOR: frozenset(_COMMON),
    Role.ADMIN: frozenset(
        _COMMON | {Permission.USERS_READ_ALL, Permission.USERS_MANAGE_ROLES, Permission.AUDIT_READ}
    ),
}


def has_permission(role: str, permission: Permission) -> bool:
    try:
        return permission in ROLE_PERMISSIONS[Role(role)]
    except ValueError:
        return False  # unknown role -> no permissions (fail closed)


def permissions_for(role: str) -> list[str]:
    try:
        return sorted(p.value for p in ROLE_PERMISSIONS[Role(role)])
    except ValueError:
        return []
