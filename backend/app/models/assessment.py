from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import JSONType

ASSESSMENT_STATUSES = ("ai_generated", "needs_review", "reviewed")


class Assessment(Base):
    """The assessment of one completed session. The original AI result is never overwritten:
    professor corrections are stored as reviews and reflected in `final_score` fields."""

    __tablename__ = "assessments"
    __table_args__ = (CheckConstraint(f"status IN {ASSESSMENT_STATUSES!r}", name="status_valid"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("simulation_sessions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ai_generated")
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rubric_snapshot: Mapped[dict] = mapped_column(JSONType, nullable=False)
    original_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_overall: Mapped[float | None] = mapped_column(Float, nullable=True)
    flags: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    report: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    criteria: Mapped[list[AssessmentCriterionResult]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentCriterionResult.position",
        lazy="selectin",
    )


class AssessmentCriterionResult(Base):
    __tablename__ = "assessment_criterion_results"
    __table_args__ = (
        UniqueConstraint("assessment_id", "criterion_id", name="uq_assessment_criterion"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criterion_id: Mapped[str] = mapped_column(String(100), nullable=False)
    competency: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    insufficient_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    qualitative_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    objective_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    original_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    level_label: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    weaknesses: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    improvements: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    uncertainty: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")

    assessment: Mapped[Assessment] = relationship(back_populates="criteria")


class AssessmentReview(Base):
    """A professor's documented correction. Append-only audit history."""

    __tablename__ = "assessment_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    criterion_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    previous_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
