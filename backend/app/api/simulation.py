"""Scenarios, simulation sessions and their assessments (student-facing)."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import (
    IdempotencyKey,
    engine_http_error,
    load_session_for,
    not_found,
)
from app.core.config import Settings
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentReview
from app.models.course import CourseAssignment, CourseMember
from app.models.simulation import SimulationSession
from app.models.user import User
from app.schemas.common import StrictModel
from app.security.dependencies import get_settings_dep, require_permission
from app.security.permissions import Permission, has_permission
from app.services import assessment as assessment_service
from app.services import scenarios as scenario_service
from app.services import sessions as session_service
from app.services.progress import scenario_of_session
from app.simulation.engine import EngineError

router = APIRouter(tags=["simulation"])
Player = Depends(require_permission(Permission.SCENARIOS_PLAY))


class StartSession(StrictModel):
    scenario_slug: str = Field(max_length=100)
    mode: Literal["training", "assessment"] = "training"
    difficulty: Literal["beginner", "intermediate", "advanced", "professional"] = "beginner"
    assignment_id: uuid.UUID | None = None


class ActionIn(StrictModel):
    action_id: str = Field(max_length=60)
    justification: str = Field(default="", max_length=2000)


class MessageIn(StrictModel):
    character_id: str = Field(max_length=60)
    text: str = Field(min_length=1, max_length=2000)


class SubmissionIn(StrictModel):
    submission_id: str = Field(max_length=60)
    text: str = Field(min_length=1, max_length=20000)


# ------------------------------------------------------------------ scenarios
@router.get("/scenarios")
def list_scenarios(
    specialization: str | None = None, db: Session = Depends(get_db), user: User = Player
) -> list[dict]:
    include_unpublished = has_permission(user.role, Permission.SCENARIOS_AUTHOR)
    items = [
        scenario_service.summary(s)
        for s in scenario_service.list_scenarios(db, include_unpublished=include_unpublished)
    ]
    if specialization:
        items = [i for i in items if i["specialization"]["code"] == specialization]
    return items


@router.get("/scenarios/{slug}")
def scenario_detail(slug: str, db: Session = Depends(get_db), user: User = Player) -> dict:
    scenario = scenario_service.get_by_slug(db, slug)
    if scenario is None or scenario.current_version is None:
        raise not_found("Scenario not found")
    if scenario.status != "published" and not has_permission(
        user.role, Permission.SCENARIOS_AUTHOR
    ):
        raise not_found("Scenario not found")
    return scenario_service.detail(scenario)


# ------------------------------------------------------------------ sessions
def _session_list_item(db: Session, s: SimulationSession) -> dict:
    d = scenario_service.definition_of(s.scenario_version)
    scenario = scenario_of_session(db, s)
    assessment = db.scalar(select(Assessment).where(Assessment.session_id == s.id))
    return {
        "id": str(s.id),
        "scenario_slug": scenario.slug if scenario else None,
        "scenario_title": d.title,
        "scenario_version": s.scenario_version.version,
        "specialization": scenario.specialization.name if scenario else None,
        "mode": s.mode,
        "difficulty": s.difficulty,
        "status": s.status,
        "outcome": next((o.title for o in d.outcomes if o.id == s.outcome_id), None),
        "started_at": s.started_at.isoformat(),
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "overall_score": assessment.final_overall if assessment else None,
        "assessment_id": str(assessment.id) if assessment else None,
        "assessment_status": assessment.status if assessment else None,
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def start_session(body: StartSession, db: Session = Depends(get_db), user: User = Player) -> dict:
    scenario = scenario_service.get_by_slug(db, body.scenario_slug)
    if scenario is None or scenario.status != "published":
        raise not_found("Scenario not found")
    mode, difficulty = body.mode, body.difficulty
    if body.assignment_id is not None:
        assignment = db.get(CourseAssignment, body.assignment_id)
        member = assignment and db.scalar(
            select(CourseMember.id).where(
                CourseMember.course_id == assignment.course_id, CourseMember.user_id == user.id
            )
        )
        if not assignment or not member or assignment.scenario_id != scenario.id:
            raise not_found("Assignment not found")
        mode, difficulty = assignment.mode, assignment.difficulty  # the professor decides
    try:
        session = session_service.start_session(
            db, user, scenario, mode=mode, difficulty=difficulty, assignment_id=body.assignment_id
        )
    except EngineError as exc:
        raise engine_http_error(exc) from None
    db.commit()
    return _view(db, session)


@router.get("/sessions")
def my_sessions(db: Session = Depends(get_db), user: User = Player) -> list[dict]:
    sessions = db.scalars(
        select(SimulationSession)
        .where(SimulationSession.user_id == user.id)
        .order_by(SimulationSession.started_at.desc())
    ).unique()
    return [_session_list_item(db, s) for s in sessions]


def _view(db: Session, session: SimulationSession) -> dict:
    data = session_service.view(session)
    scenario = scenario_of_session(db, session)
    data["scenario_slug"] = scenario.slug if scenario else None
    assessment = db.scalar(select(Assessment).where(Assessment.session_id == session.id))
    data["assessment_id"] = str(assessment.id) if assessment else None
    return data


@router.get("/sessions/{session_id}")
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Player) -> dict:
    session = load_session_for(db, user, session_id, write=False)
    data = _view(db, session)
    data["read_only"] = session.user_id != user.id
    return data


def _run(db: Session, fn, *args):
    try:
        result = fn(*args)
    except EngineError as exc:
        db.rollback()
        raise engine_http_error(exc) from None
    except session_service.ConflictError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail={"code": "conflict", "message": str(exc)}
        ) from None
    db.commit()
    return result


@router.post("/sessions/{session_id}/actions")
def perform_action(
    session_id: uuid.UUID,
    body: ActionIn,
    key: str | None = IdempotencyKey,
    db: Session = Depends(get_db),
    user: User = Player,
) -> dict:
    session = load_session_for(db, user, session_id, write=True)
    result = _run(
        db, session_service.perform_action, db, session, body.action_id, body.justification, key
    )
    return {"result": result, "view": _view(db, session)}


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: uuid.UUID,
    body: MessageIn,
    key: str | None = IdempotencyKey,
    db: Session = Depends(get_db),
    user: User = Player,
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    session = load_session_for(db, user, session_id, write=True)
    result = _run(
        db,
        session_service.send_message,
        db,
        settings,
        session,
        user,
        body.character_id,
        body.text,
        key,
    )
    return {"result": result, "view": _view(db, session)}


@router.post("/sessions/{session_id}/submissions")
def submit(
    session_id: uuid.UUID,
    body: SubmissionIn,
    key: str | None = IdempotencyKey,
    db: Session = Depends(get_db),
    user: User = Player,
) -> dict:
    session = load_session_for(db, user, session_id, write=True)
    result = _run(db, session_service.submit_work, db, session, body.submission_id, body.text, key)
    return {"result": result, "view": _view(db, session)}


@router.post("/sessions/{session_id}/hint")
def hint(
    session_id: uuid.UUID,
    key: str | None = IdempotencyKey,
    db: Session = Depends(get_db),
    user: User = Player,
) -> dict:
    session = load_session_for(db, user, session_id, write=True)
    result = _run(db, session_service.take_hint, db, session, key)
    return {"result": result, "view": _view(db, session)}


@router.post("/sessions/{session_id}/finish")
def finish(
    session_id: uuid.UUID,
    key: str | None = IdempotencyKey,
    db: Session = Depends(get_db),
    user: User = Player,
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    session = load_session_for(db, user, session_id, write=True)
    if session.status == "active":
        _run(db, session_service.finish, db, session, key)
    if session.status != "completed":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "not_completed", "message": "Session is not completed."},
        )
    assessment = assessment_service.assess_session(db, settings, session, user)
    db.commit()
    return {"outcome_id": session.outcome_id, "assessment_id": str(assessment.id)}


@router.post("/sessions/{session_id}/abandon")
def abandon(session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Player) -> dict:
    session = load_session_for(db, user, session_id, write=True)
    _run(db, session_service.abandon, db, session)
    return {"status": session.status}


@router.get("/sessions/{session_id}/timeline")
def timeline(
    session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Player
) -> list[dict]:
    session = load_session_for(db, user, session_id, write=False)
    return [
        {
            "seq": e.seq,
            "kind": e.kind,
            "actor": e.actor,
            "minute": e.sim_minute,
            "payload": e.payload,
            "created_at": e.created_at.isoformat(),
        }
        for e in session_service.events_of(db, session.id)
    ]


def assessment_payload(db: Session, assessment: Assessment) -> dict:
    session = db.get(SimulationSession, assessment.session_id)
    d = scenario_service.definition_of(session.scenario_version)  # type: ignore[union-attr]
    names = {c.id: c for c in d.rubric.criteria}
    reviews = db.scalars(
        select(AssessmentReview)
        .where(AssessmentReview.assessment_id == assessment.id)
        .order_by(AssessmentReview.created_at)
    )
    return {
        "id": str(assessment.id),
        "session_id": str(assessment.session_id),
        "student_id": str(session.user_id),  # type: ignore[union-attr]
        "status": assessment.status,
        "provider": assessment.provider,
        "model": assessment.model,
        "is_mock": assessment.is_mock,
        "original_overall": assessment.original_overall,
        "final_overall": assessment.final_overall,
        "flags": assessment.flags,
        "mode": session.mode,  # type: ignore[union-attr]
        "difficulty": session.difficulty,  # type: ignore[union-attr]
        "created_at": assessment.created_at.isoformat(),
        "criteria": [
            {
                "criterion_id": c.criterion_id,
                "name": names[c.criterion_id].name if c.criterion_id in names else c.criterion_id,
                "description": names[c.criterion_id].description if c.criterion_id in names else "",
                "competency": c.competency,
                "weight": c.weight,
                "insufficient_evidence": c.insufficient_evidence,
                "qualitative_score": c.qualitative_score,
                "objective_score": c.objective_score,
                "original_score": c.original_score,
                "final_score": c.final_score,
                "level_label": c.level_label,
                "explanation": c.explanation,
                "evidence": c.evidence,
                "weaknesses": c.weaknesses,
                "improvements": c.improvements,
                "uncertainty": c.uncertainty,
            }
            for c in assessment.criteria
        ],
        "report": assessment.report,
        "reviews": [
            {
                "criterion_id": r.criterion_id,
                "previous_score": r.previous_score,
                "new_score": r.new_score,
                "justification": r.justification,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ],
    }


@router.get("/sessions/{session_id}/assessment")
def session_assessment(
    session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Player
) -> dict:
    session = load_session_for(db, user, session_id, write=False)
    assessment = db.scalar(select(Assessment).where(Assessment.session_id == session.id))
    if assessment is None:
        raise not_found("No assessment yet")
    return assessment_payload(db, assessment)
