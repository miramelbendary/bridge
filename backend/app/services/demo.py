"""Fictional demonstration data for local runs and university demos.

Creates demo accounts, a course with an assignment, sample teaching notes, and one completed
attempt so the professor and student dashboards have something to show. Idempotent: running it
again does not duplicate anything. Never available in production.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.course import Course, CourseAssignment, CourseMember
from app.models.knowledge import EducationalResource
from app.models.simulation import SimulationSession
from app.models.specialization import Specialization
from app.models.user import Role, User
from app.services import assessment as assessment_service
from app.services import scenarios as scenario_service
from app.services import sessions as session_service
from app.services.knowledge import create_resource
from app.services.users import get_user_by_email, register_local_user, update_profile

DEMO_PASSWORD = "bridge-demo-2026"  # noqa: S105 - published demo credential, local only
DEMO_ACCOUNTS = [
    ("demo.student@example.com", "Amira (demo student)", Role.STUDENT, "international_trade"),
    ("demo.student2@example.com", "Omar (demo student)", Role.STUDENT, "translation"),
    ("demo.professor@example.com", "Dr. Salma (demo professor)", Role.PROFESSOR, None),
    ("demo.admin@example.com", "Platform admin (demo)", Role.ADMIN, None),
]
RESOURCE_DIR = Path(__file__).resolve().parent / "demo_resources"


def _user(db: Session, email: str, name: str, role: Role, spec: str | None) -> tuple[User, bool]:
    user = get_user_by_email(db, email)
    if user is not None:
        return user, False
    user = register_local_user(db, email=email, password=DEMO_PASSWORD, display_name=name)
    user.role = role.value
    if spec:
        update_profile(db, user, display_name=None, specialization_code=spec)
    db.flush()
    return user, True


def seed(db: Session, settings: Settings) -> list[str]:
    log = []
    users = {}
    for email, name, role, spec in DEMO_ACCOUNTS:
        user, created = _user(db, email, name, role, spec)
        users[email] = user
        log.append(f"{'created' if created else 'exists '} {role.value:<9} {email}")

    professor = users["demo.professor@example.com"]
    course = db.scalar(
        select(Course).where(Course.name == "BRIDGE Demo Course", Course.owner_id == professor.id)
    )
    if course is None:
        course = Course(name="BRIDGE Demo Course", owner_id=professor.id)
        db.add(course)
        db.flush()
        log.append("created course 'BRIDGE Demo Course'")
    for email in ("demo.student@example.com", "demo.student2@example.com"):
        sid = users[email].id
        if not db.scalar(
            select(CourseMember.id).where(
                CourseMember.course_id == course.id, CourseMember.user_id == sid
            )
        ):
            db.add(CourseMember(course_id=course.id, user_id=sid))

    scenario = scenario_service.get_by_slug(db, "delayed-shipment")
    if scenario and not db.scalar(
        select(CourseAssignment.id).where(CourseAssignment.course_id == course.id)
    ):
        db.add(
            CourseAssignment(
                course_id=course.id,
                scenario_id=scenario.id,
                mode="assessment",
                difficulty="beginner",
            )
        )
        log.append("assigned 'delayed-shipment' (assessment, beginner) to the demo course")

    for path in sorted(RESOURCE_DIR.glob("*.md")):
        title = path.stem.replace("-", " ").title() + " (sample notes)"
        if db.scalar(select(EducationalResource.id).where(EducationalResource.title == title)):
            continue
        code = path.stem.split("-")[0]
        spec_code = {
            "trade": "international_trade",
            "translation": "translation",
            "infocom": "infocom",
        }.get(code)
        spec = (
            db.scalar(select(Specialization).where(Specialization.code == spec_code))
            if spec_code
            else None
        )
        create_resource(
            db,
            title=title,
            filename=path.name,
            text=path.read_text(encoding="utf-8"),
            specialization_id=spec.id if spec else None,
            visibility="students",
            uploaded_by=professor.id,
        )
        log.append(f"added sample resource '{title}'")

    # One completed, assessed attempt for the second demo student, so dashboards are not empty.
    student2 = users["demo.student2@example.com"]
    if scenario and not db.scalar(
        select(SimulationSession.id).where(SimulationSession.user_id == student2.id)
    ):
        session = session_service.start_session(
            db, student2, scenario, mode="training", difficulty="beginner"
        )
        db.flush()
        why = "The supplier missed the CIF shipment date through its own late documents, so Clause 7 applies."
        for action_id, justification in [
            ("review_shipment_documents", ""),
            ("request_transport_quotes", ""),
            ("choose_wait_next_vessel", "It is the cheapest option and keeps us within budget."),
        ]:
            session_service.perform_action(db, session, action_id, justification, None)
        session_service.submit_work(
            db,
            session,
            "resolution_plan",
            "Situation: the supplier shipment is three days late. We will wait for the next vessel "
            "because it costs nothing extra and protects the budget. I will tell the customer the new "
            "date. Risks: the customer may apply the penalty clause and the port may be congested. "
            "Next steps: confirm the new booking with the supplier, send the customer an update, and "
            "monitor the vessel. " + why,
            None,
        )
        session_service.finish(db, session, None)
        assessment_service.assess_session(db, settings, session, student2)
        log.append("created one completed demo attempt for demo.student2")
    return log
