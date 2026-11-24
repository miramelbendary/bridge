"""ORM models. Import every model here so Alembic autogenerate sees the full metadata."""

from app.db.base import Base
from app.models.assessment import Assessment, AssessmentCriterionResult, AssessmentReview
from app.models.audit import AuditLog
from app.models.course import Course, CourseAssignment, CourseMember
from app.models.knowledge import EducationalResource, ResourceChunk
from app.models.platform import AIUsageLog, PlatformSetting
from app.models.scenario import Scenario, ScenarioVersion
from app.models.simulation import SessionEvent, SimulationSession
from app.models.specialization import Specialization
from app.models.user import Role, User, UserProfile

__all__ = [
    "AIUsageLog",
    "Assessment",
    "AssessmentCriterionResult",
    "AssessmentReview",
    "AuditLog",
    "Base",
    "Course",
    "CourseAssignment",
    "CourseMember",
    "EducationalResource",
    "PlatformSetting",
    "ResourceChunk",
    "Role",
    "Scenario",
    "ScenarioVersion",
    "SessionEvent",
    "SimulationSession",
    "Specialization",
    "User",
    "UserProfile",
]
