from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db, utcnow
from ..models.availability import AvailabilitySlot
from ..models.mentor import Mentor
from ..models.user import User
from ..models.booking import Booking
from ..schemas.mentor import BusyRangeOut, MentorCreate, MentorOut, MentorUpdate, ReviewOut, SlotOut, SlotsReplaceIn, VerificationOut, VerificationPath
from ..security import get_current_user, require_role
from ..services.avatars import avatar_for
from ..services.serializers import mentor_to_dict, slot_to_dict, verification_to_dict
from ..services.uploads import save_verification_document

router = APIRouter(prefix="/mentors", tags=["Mentors"])


@router.get("/", response_model=list[MentorOut])
def list_mentors(
    q: str | None = Query(default=None, description="Search name, expertise or bio"),
    expertise: str | None = Query(default=None, description="Must include this skill, e.g. 'React'"),
    mode: Literal["meet", "teams", "offline"] | None = Query(default=None, description="Meeting mode offered"),
    min_rating: float = Query(default=0, ge=0, le=5, description="Minimum average rating (0-5)"),
    sort: Literal["rating", "name", "experience"] = "rating",
    db: Session = Depends(get_db),
):
    mentors = [mentor_to_dict(m) for m in db.scalars(select(Mentor))]

    if q:
        needle = q.strip().lower()
        mentors = [m for m in mentors if needle in f"{m['name']} {m['expertise']} {m['bio']} {m['department'] or ''}".lower()]
    if expertise:
        needle = expertise.strip().lower()
        mentors = [m for m in mentors if any(needle in e.lower() for e in m["expertise_list"])]
    if mode:
        mentors = [m for m in mentors if mode in m["available_modes"]]
    if min_rating:
        mentors = [m for m in mentors if (m["rating_avg"] or 0) >= min_rating]

    if sort == "name":
        mentors.sort(key=lambda m: m["name"].lower())
    elif sort == "experience":
        mentors.sort(key=lambda m: m["years_experience"], reverse=True)
    else:
        mentors.sort(key=lambda m: (m["rating_avg"] is not None, m["rating_avg"] or 0), reverse=True)
    return mentors


@router.get("/skills", response_model=list[str])
def list_skills(db: Session = Depends(get_db)):
    """Every distinct skill any mentor lists, for the filter dropdown."""
    skills: dict[str, str] = {}
    for m in db.scalars(select(Mentor)):
        for s in (p.strip() for p in (m.expertise or "").split(",")):
            if s:
                skills.setdefault(s.lower(), s)
    return sorted(skills.values(), key=str.lower)


@router.get("/me", response_model=MentorOut)
def my_profile(user: User = Depends(require_role("mentor"))):
    if not user.mentor_profile:
        raise HTTPException(status_code=404, detail="No mentor profile is linked to this account.")
    return mentor_to_dict(user.mentor_profile)


@router.put("/me", response_model=MentorOut)
def update_my_profile(payload: MentorUpdate, user: User = Depends(require_role("mentor")), db: Session = Depends(get_db)):
    mentor = user.mentor_profile
    if not mentor:
        raise HTTPException(status_code=404, detail="No mentor profile is linked to this account.")
    required_text = {"name", "expertise", "bio"}
    for field, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str) and field not in required_text:
            value = value.strip() or None  # an empty string clears optional fields such as links
        setattr(mentor, field, value)

    # Same rule as registration, checked against the fully-merged profile since this may be
    # a partial update: an institute_type still requires a name, and school/college/university
    # still requires the institute-issued unique ID (SRS point 3).
    if mentor.institute_type is not None and not mentor.institute_name:
        raise HTTPException(status_code=422, detail="institute_name is required once an institute_type is selected.")
    if mentor.institute_type in ("school", "college", "university") and not mentor.institute_unique_id:
        raise HTTPException(
            status_code=422,
            detail="institute_unique_id is required for mentors affiliated with a school, college or university.",
        )

    db.commit()
    db.refresh(mentor)
    return mentor_to_dict(mentor)


@router.get("/me/slots", response_model=list[SlotOut])
def my_slots(user: User = Depends(require_role("mentor")), db: Session = Depends(get_db)):
    if not user.mentor_profile:
        raise HTTPException(status_code=404, detail="No mentor profile is linked to this account.")
    return [slot_to_dict(s) for s in user.mentor_profile.availability_slots]


@router.put("/me/slots", response_model=list[SlotOut])
def replace_my_slots(payload: SlotsReplaceIn, user: User = Depends(require_role("mentor")), db: Session = Depends(get_db)):
    """Replaces the mentor's whole weekly availability with the given list (SRS REQ-5-1).
    An empty list opts the mentor back OUT of enforcement (bookings become unrestricted again)."""
    mentor = user.mentor_profile
    if not mentor:
        raise HTTPException(status_code=404, detail="No mentor profile is linked to this account.")

    for s in payload.slots:
        if s.start_time >= s.end_time:
            raise HTTPException(status_code=422, detail=f"Slot start time must be before end time ({s.start_time}-{s.end_time}).")

    db.query(AvailabilitySlot).filter(AvailabilitySlot.mentor_id == mentor.id).delete()
    for s in payload.slots:
        db.add(AvailabilitySlot(mentor_id=mentor.id, weekday=s.weekday, start_time=s.start_time, end_time=s.end_time))
    db.commit()
    db.refresh(mentor)
    return [slot_to_dict(s) for s in mentor.availability_slots]


@router.get("/{mentor_id}/busy", response_model=list[BusyRangeOut])
def get_busy_ranges(mentor_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every currently-occupied time range for this mentor (pending or confirmed bookings,
    from now onward), with no indication of who booked it -- powers the color-coded slot
    picker (red = taken) the same way a ticket-booking seat map works. The mentor's own
    declared weekly windows (separately available via GET /mentors/{id}) supply the
    green-vs-gray distinction; this endpoint only ever answers "is this moment free."""
    if not db.get(Mentor, mentor_id):
        raise HTTPException(status_code=404, detail="Mentor not found.")
    rows = db.scalars(
        select(Booking).where(
            Booking.mentor_id == mentor_id,
            Booking.status.in_(("pending", "confirmed")),
            Booking.scheduled_at > utcnow(),
        )
    )
    return [
        {"start": b.scheduled_at, "end": b.scheduled_at + timedelta(minutes=b.duration_minutes)}
        for b in rows
    ]


@router.get("/{mentor_id}/reviews", response_model=list[ReviewOut])
def get_reviews(mentor_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every completed, rated session for this mentor, newest first -- for the public profile
    page's review list. No student identity is included, same privacy stance as /busy."""
    if not db.get(Mentor, mentor_id):
        raise HTTPException(status_code=404, detail="Mentor not found.")
    rows = db.scalars(
        select(Booking)
        .where(Booking.mentor_id == mentor_id, Booking.status == "completed", Booking.rating.isnot(None))
        .order_by(Booking.scheduled_at.desc())
        .limit(50)
    )
    return [{"rating": b.rating, "feedback": b.feedback, "session_date": b.scheduled_at} for b in rows]


@router.get("/{mentor_id}", response_model=MentorOut)
def get_mentor(mentor_id: int, db: Session = Depends(get_db)):
    mentor = db.get(Mentor, mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found.")
    return mentor_to_dict(mentor)


@router.get("/me/verification", response_model=VerificationOut)
def my_verification(user: User = Depends(require_role("mentor"))):
    if not user.mentor_profile:
        raise HTTPException(status_code=404, detail="No mentor profile is linked to this account.")
    return verification_to_dict(user.mentor_profile)


@router.post("/me/verification", response_model=VerificationOut, status_code=status.HTTP_201_CREATED)
async def submit_verification(
    path: VerificationPath = Form(..., description="industry | academic | coaching | community"),
    document: UploadFile = File(...),
    user: User = Depends(require_role("mentor")),
    db: Session = Depends(get_db),
):
    """Upload a credential document (PDF/JPG/PNG, max 5MB) and request review (SRS 4.2)."""
    mentor = user.mentor_profile
    if not mentor:
        raise HTTPException(status_code=404, detail="No mentor profile is linked to this account.")
    if mentor.verification_status == "verified":
        raise HTTPException(status_code=409, detail="This profile is already Platform Verified.")

    display_name, stored_path = await save_verification_document(mentor.id, document)

    mentor.verification_path = path
    mentor.verification_document_name = display_name
    mentor.verification_document_path = stored_path
    mentor.verification_status = "pending"
    mentor.verification_rejection_reason = None
    mentor.verification_submitted_at = utcnow().isoformat()
    mentor.verification_reviewed_at = None
    mentor.verification_reviewed_by = None
    db.commit()
    db.refresh(mentor)
    return verification_to_dict(mentor)


@router.post("/", response_model=MentorOut, status_code=status.HTTP_201_CREATED)
def create_mentor_profile(payload: MentorCreate, db: Session = Depends(get_db)):
    """Create a mentor profile. `user_id` is optional, so this works straight from /docs with just name, expertise and bio."""
    if not settings.ALLOW_OPEN_MENTOR_CREATION:
        raise HTTPException(status_code=403, detail="Creating mentor profiles directly is disabled. Register a mentor account instead.")
    if payload.user_id is not None:
        user = db.get(User, payload.user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"No user with id {payload.user_id}.")
        if user.mentor_profile:
            raise HTTPException(status_code=409, detail="That user already has a mentor profile.")

    data = payload.model_dump()
    data["avatar_url"] = data["avatar_url"] or avatar_for(payload.name)
    mentor = Mentor(**data)
    db.add(mentor)
    db.commit()
    db.refresh(mentor)
    return mentor_to_dict(mentor)