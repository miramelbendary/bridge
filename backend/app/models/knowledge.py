from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EducationalResource(Base):
    """Professor-approved teaching material used for grounded feedback and citations."""

    __tablename__ = "educational_resources"
    __table_args__ = (
        CheckConstraint("visibility IN ('students', 'professors')", name="visibility_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    specialization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("specializations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # "professors" = answer keys / assessment references: never shown or cited to students.
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="students")
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    chunks: Mapped[list[ResourceChunk]] = relationship(
        cascade="all, delete-orphan", order_by="ResourceChunk.position", lazy="selectin"
    )


class ResourceChunk(Base):
    __tablename__ = "resource_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("educational_resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
