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
    SCENARIOS_PLAY = "scenarios:play"
    SCENARIOS_AUTHOR = "scenarios:author"
    SCENARIOS_PUBLISH = "scenarios:publish"
    COURSES_MANAGE = "courses:manage"
    ASSESSMENTS_REVIEW = "assessments:review"
    RESOURCES_MANAGE = "resources:manage"
    RESOURCES_READ = "resources:read"
    PLATFORM_MANAGE = "platform:manage"
    USAGE_READ = "usage:read"
    SPECIALIZATIONS_MANAGE = "specializations:manage"


_COMMON = {
    Permission.PROFILE_READ_OWN,
    Permission.PROFILE_UPDATE_OWN,
    Permission.SPECIALIZATIONS_READ,
    Permission.SCENARIOS_PLAY,
    Permission.RESOURCES_READ,
}

_TEACHING = {
    Permission.SCENARIOS_AUTHOR,
    Permission.COURSES_MANAGE,
    Permission.ASSESSMENTS_REVIEW,
    Permission.RESOURCES_MANAGE,
}

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.STUDENT: frozenset(_COMMON),
    # Professors review only students in their own courses (enforced in services/access.py).
    # They must NOT get users:read_all.
    Role.PROFESSOR: frozenset(_COMMON | _TEACHING),
    Role.ADMIN: frozenset(
        _COMMON
        | _TEACHING
        | {
            Permission.USERS_READ_ALL,
            Permission.USERS_MANAGE_ROLES,
            Permission.AUDIT_READ,
            Permission.SCENARIOS_PUBLISH,
            Permission.PLATFORM_MANAGE,
            Permission.USAGE_READ,
            Permission.SPECIALIZATIONS_MANAGE,
        }
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
