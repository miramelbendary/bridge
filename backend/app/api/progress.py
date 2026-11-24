"""Student progress: competency profile, recommendations, assignments, resources."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.course import Course, CourseAssignment, CourseMember
from app.models.scenario import Scenario
from app.models.simulation import SimulationSession
from app.models.user import User
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.services import knowledge, progress
from app.services.scenarios import definition_of

router = APIRouter(prefix="/me", tags=["progress"])
Player = Depends(require_permission(Permission.SCENARIOS_PLAY))


@router.get("/competencies")
def competencies(db: Session = Depends(get_db), user: User = Player) -> list[dict]:
    return progress.competency_profile(db, user.id)


@router.get("/recommendations")
def recommendations(db: Session = Depends(get_db), user: User = Player) -> list[dict]:
    return progress.recommendations(db, user)


@router.get("/assignments")
def assignments(db: Session = Depends(get_db), user: User = Player) -> list[dict]:
    rows = db.execute(
        select(CourseAssignment, Course, Scenario)
        .join(Course, Course.id == CourseAssignment.course_id)
        .join(CourseMember, CourseMember.course_id == Course.id)
        .join(Scenario, Scenario.id == CourseAssignment.scenario_id)
        .where(CourseMember.user_id == user.id, Scenario.status == "published")
        .order_by(CourseAssignment.due_at)
    ).all()
    out = []
    for a, course, scenario in rows:
        done = db.scalar(
            select(SimulationSession.id).where(
                SimulationSession.assignment_id == a.id,
                SimulationSession.user_id == user.id,
                SimulationSession.status == "completed",
            )
        )
        out.append(
            {
                "id": str(a.id),
                "course": course.name,
                "scenario_slug": scenario.slug,
                "scenario_title": definition_of(scenario.current_version).title,  # type: ignore[arg-type]
                "mode": a.mode,
                "difficulty": a.difficulty,
                "due_at": a.due_at.isoformat() if a.due_at else None,
                "completed": done is not None,
            }
        )
    return out


@router.get("/resources/search")
def search_resources(
    q: str = Query(min_length=2, max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.RESOURCES_READ)),
) -> list[dict]:
    spec = user.profile.specialization_id if user.profile else None
    return knowledge.search(db, q, specialization_id=spec, include_professor_only=False, limit=5)
