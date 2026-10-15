from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.mentor import Mentor
from ..models.student import StudentProfile
from ..models.user import User
from ..schemas.user import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, get_current_user, hash_password, verify_password
from ..services.avatars import avatar_for
from ..services.serializers import user_to_dict

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists. Try signing in.")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        avatar_url=avatar_for(payload.full_name),
    )
    db.add(user)
    db.flush()

    if payload.role == "mentor":
        db.add(
            Mentor(
                user_id=user.id,
                name=payload.full_name,
                expertise=payload.expertise or "",
                bio=payload.bio or "",
                avatar_url=user.avatar_url,
                institute_type=payload.institute_type,
                institute_name=payload.institute_name,
                institute_unique_id=payload.institute_unique_id,
            )
        )
    else:
        db.add(
            StudentProfile(
                user_id=user.id,
                institute_type=payload.institute_type,
                institute_name=payload.institute_name,
                roll_number=payload.roll_number,
                program_level=payload.program_level,
                year_of_study=payload.year_of_study,
                branch=payload.branch,
            )
        )
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user), "user": user_to_dict(user)}


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"access_token": create_access_token(user), "user": user_to_dict(user)}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user_to_dict(user)