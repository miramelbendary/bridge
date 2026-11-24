from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.specialization import Specialization


class Role(enum.StrEnum):
    STUDENT = "student"
    PROFESSOR = "professor"
    ADMIN = "admin"


ROLE_VALUES = tuple(r.value for r in Role)
AUTH_PROVIDERS = ("local", "supabase")


class User(TimestampMixin, Base):
    """An account. Identity comes from an auth provider; the role is always owned by BRIDGE."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role IN {ROLE_VALUES!r}", name="role_valid"),
        CheckConstraint(f"auth_provider IN {AUTH_PROVIDERS!r}", name="auth_provider_valid"),
        # Local accounts must have a password hash; external accounts must have a subject.
        CheckConstraint(
            "(auth_provider = 'local' AND password_hash IS NOT NULL) OR "
            "(auth_provider <> 'local' AND auth_subject IS NOT NULL)",
            name="credentials_present",
        ),
        UniqueConstraint("auth_provider", "auth_subject", name="uq_users_provider_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    auth_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=Role.STUDENT.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped[UserProfile] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )


class UserProfile(TimestampMixin, Base):
    """Minimal profile. Deliberately holds no extra personal data (see SECURITY.md)."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    specialization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("specializations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped[User] = relationship(back_populates="profile")
    specialization: Mapped[Specialization | None] = relationship(lazy="joined")
