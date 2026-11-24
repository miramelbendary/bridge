"""Ownership and course-based authorization rules.

* Students see only their own sessions and assessments.
* Professors see students who are members of a course they own.
* Administrators see everything.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course, CourseMember
from app.models.user import Role, User


def professor_can_see(db: Session, professor_id: uuid.UUID, student_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(CourseMember.id)
            .join(Course, Course.id == CourseMember.course_id)
            .where(Course.owner_id == professor_id, CourseMember.user_id == student_id)
            .limit(1)
        )
        is not None
    )


def can_view_student_data(db: Session, viewer: User, student_id: uuid.UUID) -> bool:
    if viewer.id == student_id or viewer.role == Role.ADMIN.value:
        return True
    if viewer.role == Role.PROFESSOR.value:
        return professor_can_see(db, viewer.id, student_id)
    return False


def can_review(db: Session, viewer: User, student_id: uuid.UUID) -> bool:
    if viewer.role == Role.ADMIN.value:
        return True
    return viewer.role == Role.PROFESSOR.value and professor_can_see(db, viewer.id, student_id)


def owned_course(db: Session, user: User, course_id: uuid.UUID) -> Course | None:
    course = db.get(Course, course_id)
    if course is None:
        return None
    if course.owner_id == user.id or user.role == Role.ADMIN.value:
        return course
    return None
