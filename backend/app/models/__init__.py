"""ORM models. Import every model here so Alembic autogenerate sees the full metadata."""

from app.db.base import Base
from app.models.audit import AuditLog
from app.models.specialization import Specialization
from app.models.user import Role, User, UserProfile

__all__ = ["AuditLog", "Base", "Role", "Specialization", "User", "UserProfile"]
