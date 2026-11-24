from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.types import JSONType
from app.models.specialization import Specialization

SCENARIO_STATUSES = ("draft", "published", "archived")


class Scenario(TimestampMixin, Base):
    """A scenario identity. Its content lives in immutable, numbered versions."""

    __tablename__ = "scenarios"
    __table_args__ = (CheckConstraint(f"status IN {SCENARIO_STATUSES!r}", name="status_valid"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    specialization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # The version new sessions use. Older sessions keep pointing at the version they started on.
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("scenario_versions.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    specialization: Mapped[Specialization] = relationship(lazy="joined")
    current_version: Mapped[ScenarioVersion | None] = relationship(
        foreign_keys=[current_version_id], lazy="joined", post_update=True
    )


class ScenarioVersion(Base):
    """Immutable snapshot of a scenario definition, including its rubric."""

    __tablename__ = "scenario_versions"
    __table_args__ = (UniqueConstraint("scenario_id", "version", name="uq_scenario_versions_num"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict] = mapped_column(JSONType, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    change_note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
