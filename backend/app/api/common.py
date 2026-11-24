"""Helpers shared by route modules."""

from __future__ import annotations

import uuid

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.simulation import SimulationSession
from app.models.user import User
from app.services import access
from app.simulation.engine import EngineError

IdempotencyKey = Header(default=None, alias="Idempotency-Key", max_length=100)


def engine_http_error(exc: EngineError) -> HTTPException:
    code = (
        status.HTTP_409_CONFLICT if exc.code in ("session_finished", "action_unavailable") else 422
    )
    return HTTPException(status_code=code, detail={"code": exc.code, "message": exc.message})


def not_found(what: str = "Not found") -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=what)


def load_session_for(
    db: Session, user: User, session_id: uuid.UUID, *, write: bool
) -> SimulationSession:
    """Owner may read and write. Authorized professors/admins may only read.
    Anyone else gets 404 (no information about other students' sessions leaks)."""
    session = db.get(SimulationSession, session_id)
    if session is None:
        raise not_found("Session not found")
    if session.user_id == user.id:
        return session
    if not write and access.can_view_student_data(db, user, session.user_id):
        return session
    raise not_found("Session not found")


def load_assessment_for(db: Session, user: User, assessment_id: uuid.UUID) -> Assessment:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise not_found("Assessment not found")
    session = db.get(SimulationSession, assessment.session_id)
    if session is None or not access.can_view_student_data(db, user, session.user_id):
        raise not_found("Assessment not found")
    return assessment
