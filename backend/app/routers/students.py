from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.student import StudentProfile
from ..models.user import User
from ..schemas.student import StudentProfileOut, StudentProfileUpdate
from ..security import require_role
from ..services.serializers import student_profile_to_dict

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/me", response_model=StudentProfileOut)
def my_profile(user: User = Depends(require_role("student"))):
    return student_profile_to_dict(user.student_profile)


@router.put("/me", response_model=StudentProfileOut)
def update_my_profile(payload: StudentProfileUpdate, user: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    profile = user.student_profile
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(profile, field, value)

    # Same rule as registration: once an institute_type is set, institute_name must be too --
    # checked against the fully-merged profile, since this may be a partial update.
    if profile.institute_type is not None and not profile.institute_name:
        raise HTTPException(status_code=422, detail="institute_name is required once an institute_type is selected.")

    db.commit()
    db.refresh(profile)
    return student_profile_to_dict(profile)