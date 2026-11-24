"""User account business logic, independent of HTTP."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.specialization import Specialization
from app.models.user import Role, User, UserProfile
from app.security.passwords import hash_password, verify_password
from app.security.tokens import VerifiedIdentity


class EmailAlreadyRegisteredError(Exception):
    pass


class UserProvisioningError(Exception):
    pass


class UnknownSpecializationError(Exception):
    pass


class RoleChangeError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def register_local_user(db: Session, *, email: str, password: str, display_name: str) -> User:
    """Create a local student account. Roles above student are only granted by an administrator."""
    email = normalize_email(email)
    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError(email)
    user = User(
        email=email,
        auth_provider="local",
        password_hash=hash_password(password),
        role=Role.STUDENT.value,
        is_active=True,
    )
    user.profile = UserProfile(display_name=display_name.strip())
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent registration with the same email
        db.rollback()
        raise EmailAlreadyRegisteredError(email) from exc
    return user


def authenticate_local_user(db: Session, *, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    candidate_hash = user.password_hash if user and user.auth_provider == "local" else None
    if not verify_password(password, candidate_hash):  # constant work even if user is missing
        return None
    if user is None or not user.is_active:
        return None
    user.last_login_at = datetime.now(UTC)
    return user


def get_or_provision_external_user(db: Session, identity: VerifiedIdentity) -> User:
    """Find or create the BRIDGE user for a verified external (Supabase) identity.

    New external users always start as students. An external identity is never silently linked
    to an existing local account with the same email (that would allow account takeover).
    """
    user = db.scalar(
        select(User).where(
            User.auth_provider == identity.provider, User.auth_subject == identity.subject
        )
    )
    if user is not None:
        return user
    if not identity.email:
        raise UserProvisioningError("external identity has no email claim")
    if get_user_by_email(db, identity.email) is not None:
        raise UserProvisioningError("email already belongs to another account")
    user = User(
        email=identity.email,
        auth_provider=identity.provider,
        auth_subject=identity.subject,
        role=Role.STUDENT.value,
        is_active=True,
    )
    user.profile = UserProfile(display_name=identity.email.split("@", 1)[0][:120])
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # concurrent first requests for the same identity
        db.rollback()
        existing = db.scalar(
            select(User).where(
                User.auth_provider == identity.provider, User.auth_subject == identity.subject
            )
        )
        if existing is None:
            raise UserProvisioningError("could not provision external user") from exc
        return existing
    return user


def update_profile(
    db: Session, user: User, *, display_name: str | None, specialization_code: str | None
) -> User:
    if user.profile is None:
        user.profile = UserProfile(display_name=user.email.split("@", 1)[0][:120])
    if display_name is not None:
        user.profile.display_name = display_name.strip()
    if specialization_code is not None:
        spec = db.scalar(
            select(Specialization).where(
                Specialization.code == specialization_code, Specialization.is_active.is_(True)
            )
        )
        if spec is None:
            raise UnknownSpecializationError(specialization_code)
        user.profile.specialization_id = spec.id
        user.profile.specialization = spec
    return user


def change_role(db: Session, *, actor: User, target_id: uuid.UUID, new_role: Role) -> User:
    target = db.get(User, target_id)
    if target is None:
        raise LookupError("user not found")
    if target.id == actor.id and new_role != Role.ADMIN:
        raise RoleChangeError("Administrators cannot remove their own administrator role")
    if target.role == Role.ADMIN.value and new_role != Role.ADMIN:
        admin_count = db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == Role.ADMIN.value, User.is_active.is_(True))
        )
        if (admin_count or 0) <= 1:
            raise RoleChangeError("Cannot remove the last active administrator")
    target.role = new_role.value
    return target
