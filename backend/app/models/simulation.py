from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.types import JSONType
from app.models.scenario import ScenarioVersion

MODES = ("training", "assessment")
DIFFICULTIES = ("beginner", "intermediate", "advanced", "professional")
SESSION_STATUSES = ("active", "completed", "abandoned")


class SimulationSession(TimestampMixin, Base):
    """One attempt by one student at one scenario version.

    `state` is the authoritative scenario state. Only the simulation engine writes it, and every
    write increments `state_version` (optimistic concurrency control).
    """

    __tablename__ = "simulation_sessions"
    __table_args__ = (
        CheckConstraint(f"mode IN {MODES!r}", name="mode_valid"),
        CheckConstraint(f"difficulty IN {DIFFICULTIES!r}", name="difficulty_valid"),
        CheckConstraint(f"status IN {SESSION_STATUSES!r}", name="status_valid"),
        Index("ix_simulation_sessions_user_started", "user_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scenario_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("scenario_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("course_assignments.id", ondelete="SET NULL"), nullable=True
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    state: Mapped[dict] = mapped_column(JSONType, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outcome_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario_version: Mapped[ScenarioVersion] = relationship(lazy="joined")


class SessionEvent(Base):
    """Append-only, ordered history of everything that happened in a session.

    Assessment evidence references these rows by `seq`, so they are never edited or deleted
    while the session exists.
    """

    __tablename__ = "session_events"
    __table_args__ = (
        UniqueConstraint("session_id", "seq", name="uq_session_events_seq"),
        UniqueConstraint("session_id", "idempotency_key", name="uq_session_events_idem"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)  # student | system | <char id>
    sim_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
