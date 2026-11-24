from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import MeResponse, ProfileUpdate, UserRead
from app.security.dependencies import require_permission
from app.security.permissions import Permission, permissions_for
from app.services.users import UnknownSpecializationError, update_profile

router = APIRouter(prefix="/users", tags=["users"])


def _me(user: User) -> MeResponse:
    base = UserRead.model_validate(user).model_dump()
    return MeResponse(**base, permissions=permissions_for(user.role))


@router.get("/me", response_model=MeResponse)
def read_me(user: User = Depends(require_permission(Permission.PROFILE_READ_OWN))) -> MeResponse:
    return _me(user)


@router.patch("/me/profile", response_model=MeResponse)
def update_my_profile(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.PROFILE_UPDATE_OWN)),
) -> MeResponse:
    try:
        update_profile(
            db, user, display_name=body.display_name, specialization_code=body.specialization_code
        )
    except UnknownSpecializationError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown specialization"
        ) from None
    db.commit()
    db.refresh(user)
    return _me(user)
