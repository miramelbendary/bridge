"""Professor tools: courses, assignments, student progress, assessment review, scenario and rubric
authoring, educational resources, report export."""

from __future__ import annotations

import csv
import io
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import load_assessment_for, not_found
from app.api.simulation import _session_list_item, assessment_payload
from app.core.config import Settings
from app.db.session import get_db
from app.models.assessment import Assessment
from app.models.course import Course, CourseAssignment, CourseMember
from app.models.knowledge import EducationalResource
from app.models.scenario import Scenario, ScenarioVersion
from app.models.simulation import SimulationSession
from app.models.specialization import Specialization
from app.models.user import Role, User
from app.schemas.common import StrictModel
from app.security.dependencies import get_settings_dep, require_permission
from app.security.permissions import Permission
from app.security.rate_limit import client_ip
from app.services import access, audit, knowledge
from app.services import assessment as assessment_service
from app.services import scenarios as scenario_service
from app.services.users import get_user_by_email
from app.simulation.competencies import label as competency_label

router = APIRouter(prefix="/teach", tags=["teaching"])
Teacher = Depends(require_permission(Permission.COURSES_MANAGE))
Reviewer = Depends(require_permission(Permission.ASSESSMENTS_REVIEW))
Author = Depends(require_permission(Permission.SCENARIOS_AUTHOR))
ResourceManager = Depends(require_permission(Permission.RESOURCES_MANAGE))


class CourseIn(StrictModel):
    name: str = Field(min_length=2, max_length=200)
    specialization_code: str | None = Field(default=None, max_length=50)


class MemberIn(StrictModel):
    email: str = Field(min_length=3, max_length=320)


class AssignmentIn(StrictModel):
    scenario_slug: str = Field(max_length=100)
    mode: Literal["training", "assessment"] = "assessment"
    difficulty: Literal["beginner", "intermediate", "advanced", "professional"] = "beginner"
    due_at: datetime | None = None


class ReviewIn(StrictModel):
    criterion_id: str | None = Field(default=None, max_length=100)
    new_score: float | None = Field(default=None, ge=0, le=100)
    justification: str = Field(min_length=10, max_length=4000)


class DefinitionIn(StrictModel):
    definition: dict
    change_note: str = Field(default="", max_length=500)


class RubricIn(StrictModel):
    rubric: dict
    change_note: str = Field(default="", max_length=500)


class ResourceIn(StrictModel):
    title: str = Field(min_length=2, max_length=300)
    filename: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=20, max_length=2_000_000)
    visibility: Literal["students", "professors"] = "students"
    specialization_code: str | None = Field(default=None, max_length=50)


def _spec_id(db: Session, code: str | None) -> uuid.UUID | None:
    if not code:
        return None
    spec = db.scalar(select(Specialization).where(Specialization.code == code))
    if spec is None:
        raise HTTPException(422, detail="Unknown specialization")
    return spec.id


def _course_or_404(db: Session, user: User, course_id: uuid.UUID) -> Course:
    course = access.owned_course(db, user, course_id)
    if course is None:
        raise not_found("Course not found")
    return course


# ------------------------------------------------------------------ courses
@router.get("/courses")
def list_courses(db: Session = Depends(get_db), user: User = Teacher) -> list[dict]:
    query = select(Course).order_by(Course.created_at)
    if user.role != Role.ADMIN.value:
        query = query.where(Course.owner_id == user.id)
    out = []
    for c in db.scalars(query):
        members = db.scalars(select(CourseMember).where(CourseMember.course_id == c.id)).all()
        out.append({"id": str(c.id), "name": c.name, "students": len(members)})
    return out


@router.post("/courses", status_code=201)
def create_course(body: CourseIn, db: Session = Depends(get_db), user: User = Teacher) -> dict:
    course = Course(
        name=body.name, specialization_id=_spec_id(db, body.specialization_code), owner_id=user.id
    )
    db.add(course)
    db.commit()
    return {"id": str(course.id), "name": course.name, "students": 0}


@router.get("/courses/{course_id}")
def course_detail(
    course_id: uuid.UUID, db: Session = Depends(get_db), user: User = Teacher
) -> dict:
    course = _course_or_404(db, user, course_id)
    members = (
        db.execute(
            select(User)
            .join(CourseMember, CourseMember.user_id == User.id)
            .where(CourseMember.course_id == course.id)
        )
        .scalars()
        .unique()
        .all()
    )
    assignments = db.execute(
        select(CourseAssignment, Scenario)
        .join(Scenario, Scenario.id == CourseAssignment.scenario_id)
        .where(CourseAssignment.course_id == course.id)
    ).all()
    return {
        "id": str(course.id),
        "name": course.name,
        "students": [
            {
                "id": str(m.id),
                "email": m.email,
                "display_name": m.profile.display_name if m.profile else m.email,
            }
            for m in members
        ],
        "assignments": [
            {
                "id": str(a.id),
                "scenario_slug": s.slug,
                "scenario_title": scenario_service.definition_of(s.current_version).title,  # type: ignore[arg-type]
                "mode": a.mode,
                "difficulty": a.difficulty,
                "due_at": a.due_at.isoformat() if a.due_at else None,
            }
            for a, s in assignments
        ],
    }


@router.post("/courses/{course_id}/members", status_code=201)
def add_member(
    course_id: uuid.UUID,
    body: MemberIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Teacher,
) -> dict:
    course = _course_or_404(db, user, course_id)
    student = get_user_by_email(db, body.email)
    if student is None or student.role != Role.STUDENT.value:
        raise HTTPException(404, detail="No student account with that email")
    exists = db.scalar(
        select(CourseMember.id).where(
            CourseMember.course_id == course.id, CourseMember.user_id == student.id
        )
    )
    if not exists:
        db.add(CourseMember(course_id=course.id, user_id=student.id))
        audit.record(
            db,
            action="course.member_added",
            actor_user_id=user.id,
            target_type="course",
            target_id=str(course.id),
            ip_address=client_ip(request),
            details={"student_id": str(student.id)},
        )
    db.commit()
    return {"id": str(student.id), "email": student.email}


@router.delete("/courses/{course_id}/members/{student_id}", status_code=204)
def remove_member(
    course_id: uuid.UUID, student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Teacher
) -> Response:
    course = _course_or_404(db, user, course_id)
    member = db.scalar(
        select(CourseMember).where(
            CourseMember.course_id == course.id, CourseMember.user_id == student_id
        )
    )
    if member:
        db.delete(member)
        db.commit()
    return Response(status_code=204)


@router.post("/courses/{course_id}/assignments", status_code=201)
def add_assignment(
    course_id: uuid.UUID, body: AssignmentIn, db: Session = Depends(get_db), user: User = Teacher
) -> dict:
    course = _course_or_404(db, user, course_id)
    scenario = scenario_service.get_by_slug(db, body.scenario_slug)
    if scenario is None or scenario.status != "published":
        raise HTTPException(404, detail="Published scenario not found")
    d = scenario_service.definition_of(scenario.current_version)  # type: ignore[arg-type]
    if body.difficulty not in d.difficulties:
        raise HTTPException(422, detail="That difficulty is not offered by this scenario")
    a = CourseAssignment(
        course_id=course.id,
        scenario_id=scenario.id,
        mode=body.mode,
        difficulty=body.difficulty,
        due_at=body.due_at,
    )
    db.add(a)
    db.commit()
    return {"id": str(a.id)}


@router.delete("/courses/{course_id}/assignments/{assignment_id}", status_code=204)
def delete_assignment(
    course_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Teacher,
) -> Response:
    course = _course_or_404(db, user, course_id)
    a = db.get(CourseAssignment, assignment_id)
    if a and a.course_id == course.id:
        db.delete(a)
        db.commit()
    return Response(status_code=204)


def _course_rows(db: Session, course: Course):
    return db.execute(
        select(User, SimulationSession, Assessment)
        .join(CourseMember, CourseMember.user_id == User.id)
        .join(SimulationSession, SimulationSession.user_id == User.id)
        .outerjoin(Assessment, Assessment.session_id == SimulationSession.id)
        .where(CourseMember.course_id == course.id, SimulationSession.status == "completed")
        .order_by(SimulationSession.completed_at)
    ).all()


@router.get("/courses/{course_id}/progress")
def course_progress(
    course_id: uuid.UUID, db: Session = Depends(get_db), user: User = Teacher
) -> dict:
    course = _course_or_404(db, user, course_id)
    rows = _course_rows(db, course)
    per_student: dict[str, dict] = {}
    per_comp: dict[str, list[float]] = defaultdict(list)
    per_criterion: dict[str, list[float]] = defaultdict(list)
    for student, _session, assessment in rows:
        entry = per_student.setdefault(
            str(student.id),
            {
                "id": str(student.id),
                "display_name": student.profile.display_name if student.profile else student.email,
                "email": student.email,
                "attempts": 0,
                "scores": [],
                "needs_review": 0,
            },
        )
        entry["attempts"] += 1
        if assessment and assessment.final_overall is not None:
            entry["scores"].append(assessment.final_overall)
        if assessment and assessment.status == "needs_review":
            entry["needs_review"] += 1
        if assessment:
            for c in assessment.criteria:
                if c.final_score is not None:
                    per_comp[c.competency].append(c.final_score)
                    per_criterion[c.criterion_id].append(c.final_score)
    students = []
    for e in per_student.values():
        scores = e.pop("scores")
        e["average"] = round(sum(scores) / len(scores), 1) if scores else None
        e["latest"] = scores[-1] if scores else None
        students.append(e)
    weaknesses = sorted(
        (
            {
                "competency": k,
                "label": competency_label(k),
                "average": round(sum(v) / len(v), 1),
                "observations": len(v),
            }
            for k, v in per_comp.items()
        ),
        key=lambda x: x["average"],
    )
    return {"course": course.name, "students": students, "competencies": weaknesses}


@router.get("/courses/{course_id}/export.csv")
def export_course(
    course_id: uuid.UUID, db: Session = Depends(get_db), user: User = Teacher
) -> Response:
    course = _course_or_404(db, user, course_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "student",
            "email",
            "scenario",
            "version",
            "mode",
            "difficulty",
            "completed_at",
            "outcome",
            "overall_score",
            "assessment_status",
            "evaluator",
        ]
    )
    for student, session, assessment in _course_rows(db, course):
        d = scenario_service.definition_of(session.scenario_version)
        outcome = next((o.title for o in d.outcomes if o.id == session.outcome_id), "")
        writer.writerow(
            [
                student.profile.display_name if student.profile else "",
                student.email,
                d.title,
                session.scenario_version.version,
                session.mode,
                session.difficulty,
                session.completed_at.isoformat() if session.completed_at else "",
                outcome,
                assessment.final_overall if assessment else "",
                assessment.status if assessment else "",
                ("mock" if assessment.is_mock else assessment.model) if assessment else "",
            ]
        )
    filename = f"bridge-course-{course.id}.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/students/{student_id}/sessions")
def student_sessions(
    student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Reviewer
) -> dict:
    if not access.can_review(db, user, student_id):
        raise not_found("Student not found")
    student = db.get(User, student_id)
    sessions = db.scalars(
        select(SimulationSession)
        .where(SimulationSession.user_id == student_id)
        .order_by(SimulationSession.started_at.desc())
    ).unique()
    from app.services.progress import competency_profile

    return {
        "student": {
            "id": str(student.id),  # type: ignore[union-attr]
            "display_name": student.profile.display_name if student and student.profile else "",
            "email": student.email if student else "",
        },
        "sessions": [_session_list_item(db, s) for s in sessions],
        "competencies": competency_profile(db, student_id),
    }


@router.get("/review-queue")
def review_queue(db: Session = Depends(get_db), user: User = Reviewer) -> list[dict]:
    query = (
        select(Assessment, SimulationSession, User)
        .join(SimulationSession, SimulationSession.id == Assessment.session_id)
        .join(User, User.id == SimulationSession.user_id)
        .order_by(Assessment.created_at.desc())
        .limit(200)
    )
    out = []
    for a, s, student in db.execute(query).unique().all():
        if not access.can_review(db, user, student.id):
            continue
        d = scenario_service.definition_of(s.scenario_version)
        out.append(
            {
                "assessment_id": str(a.id),
                "session_id": str(s.id),
                "student": student.profile.display_name if student.profile else student.email,
                "scenario": d.title,
                "mode": s.mode,
                "status": a.status,
                "overall": a.final_overall,
                "flags": a.flags,
                "is_mock": a.is_mock,
                "created_at": a.created_at.isoformat(),
            }
        )
    return out


@router.get("/assessments/{assessment_id}")
def get_assessment(
    assessment_id: uuid.UUID, db: Session = Depends(get_db), user: User = Reviewer
) -> dict:
    assessment = load_assessment_for(db, user, assessment_id)
    return assessment_payload(db, assessment)


@router.post("/assessments/{assessment_id}/reviews")
def review_assessment(
    assessment_id: uuid.UUID,
    body: ReviewIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Reviewer,
) -> dict:
    assessment = load_assessment_for(db, user, assessment_id)
    session = db.get(SimulationSession, assessment.session_id)
    if session is None or not access.can_review(db, user, session.user_id):
        raise not_found("Assessment not found")
    try:
        assessment_service.apply_review(
            db,
            assessment,
            user,
            criterion_id=body.criterion_id,
            new_score=body.new_score,
            justification=body.justification,
        )
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None
    audit.record(
        db,
        action="assessment.reviewed",
        actor_user_id=user.id,
        target_type="assessment",
        target_id=str(assessment.id),
        ip_address=client_ip(request),
        details={"criterion_id": body.criterion_id, "new_score": body.new_score},
    )
    db.commit()
    return assessment_payload(db, assessment)


# ------------------------------------------------------------------ authoring
@router.get("/scenarios/{slug}/definition")
def get_definition(slug: str, db: Session = Depends(get_db), user: User = Author) -> dict:
    scenario = scenario_service.get_by_slug(db, slug)
    if scenario is None or scenario.current_version is None:
        raise not_found("Scenario not found")
    versions = db.scalars(
        select(ScenarioVersion)
        .where(ScenarioVersion.scenario_id == scenario.id)
        .order_by(ScenarioVersion.version.desc())
    )
    return {
        "slug": scenario.slug,
        "status": scenario.status,
        "version": scenario.current_version.version,
        "definition": scenario.current_version.definition,
        "versions": [
            {
                "version": v.version,
                "change_note": v.change_note,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ],
    }


@router.post("/scenarios/validate")
def validate_definition(body: DefinitionIn, user: User = Author) -> dict:
    try:
        d = scenario_service.validate_definition(body.definition)
    except scenario_service.ScenarioValidationError as exc:
        return {"valid": False, "errors": exc.errors}
    return {"valid": True, "errors": [], "title": d.title}


@router.post("/scenarios", status_code=201)
def save_definition(
    body: DefinitionIn, request: Request, db: Session = Depends(get_db), user: User = Author
) -> dict:
    try:
        d = scenario_service.validate_definition(body.definition)
        scenario, version, created = scenario_service.save_version(
            db, d, author=user, change_note=body.change_note or "Edited in scenario editor"
        )
    except scenario_service.ScenarioValidationError as exc:
        raise HTTPException(
            422, detail={"code": "invalid_scenario", "errors": exc.errors}
        ) from None
    audit.record(
        db,
        action="scenario.version_saved",
        actor_user_id=user.id,
        target_type="scenario",
        target_id=scenario.slug,
        ip_address=client_ip(request),
        details={"version": version.version, "created": created},
    )
    db.commit()
    return {
        "slug": scenario.slug,
        "version": version.version,
        "created": created,
        "status": scenario.status,
    }


@router.put("/scenarios/{slug}/rubric")
def save_rubric(
    slug: str, body: RubricIn, request: Request, db: Session = Depends(get_db), user: User = Author
) -> dict:
    scenario = scenario_service.get_by_slug(db, slug)
    if scenario is None or scenario.current_version is None:
        raise not_found("Scenario not found")
    data = dict(scenario.current_version.definition)
    data["rubric"] = body.rubric
    return save_definition(
        DefinitionIn(definition=data, change_note=body.change_note or "Rubric edited"),
        request,
        db,
        user,
    )


# ------------------------------------------------------------------ resources
@router.get("/resources")
def list_resources(db: Session = Depends(get_db), user: User = ResourceManager) -> list[dict]:
    resources = db.scalars(
        select(EducationalResource).order_by(EducationalResource.created_at.desc())
    )
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "filename": r.source_filename,
            "visibility": r.visibility,
            "version": r.version,
            "chunks": len(r.chunks),
            "created_at": r.created_at.isoformat(),
        }
        for r in resources
    ]


@router.post("/resources", status_code=201)
def upload_resource(
    body: ResourceIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = ResourceManager,
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    try:
        text = knowledge.extract_text(
            body.filename, body.content.encode("utf-8"), settings.max_upload_bytes
        )
        resource = knowledge.create_resource(
            db,
            title=body.title,
            filename=body.filename,
            text=text,
            specialization_id=_spec_id(db, body.specialization_code),
            visibility=body.visibility,
            uploaded_by=user.id,
        )
    except knowledge.ResourceError as exc:
        raise HTTPException(422, detail=str(exc)) from None
    audit.record(
        db,
        action="resource.uploaded",
        actor_user_id=user.id,
        target_type="resource",
        target_id=str(resource.id),
        ip_address=client_ip(request),
        details={"visibility": body.visibility},
    )
    db.commit()
    return {"id": str(resource.id), "version": resource.version, "chunks": len(resource.chunks)}


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(
    resource_id: uuid.UUID, db: Session = Depends(get_db), user: User = ResourceManager
) -> Response:
    resource = db.get(EducationalResource, resource_id)
    if resource is None:
        raise not_found("Resource not found")
    if resource.uploaded_by_id != user.id and user.role != Role.ADMIN.value:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only the uploader or an administrator can delete this",
        )
    db.delete(resource)
    db.commit()
    return Response(status_code=204)
