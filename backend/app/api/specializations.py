from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.specialization import Specialization
from app.schemas.user import SpecializationRead
from app.security.dependencies import require_permission
from app.security.permissions import Permission

router = APIRouter(prefix="/specializations", tags=["specializations"])


@router.get(
    "",
    response_model=list[SpecializationRead],
    dependencies=[Depends(require_permission(Permission.SPECIALIZATIONS_READ))],
)
def list_specializations(db: Session = Depends(get_db)) -> list[Specialization]:
    return list(
        db.scalars(
            select(Specialization)
            .where(Specialization.is_active.is_(True))
            .order_by(Specialization.name)
        )
    )
