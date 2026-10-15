from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..models.booking import Booking
from ..models.mentor import Mentor
from ..models.user import User
from ..schemas.booking import BookingCreate, BookingOut, BookingStatusUpdate, LocationUpdateIn, RescheduleIn, ReviewIn
from ..security import get_current_user, require_role
from ..services import notifications
from ..services.availability import fits_within_availability
from ..services.serializers import available_modes, booking_to_dict

router = APIRouter(prefix="/bookings", tags=["Bookings"])

ACTIVE = ("pending", "confirmed")


def _overlaps(existing: Booking, start, end, ignore_id: int | None = None) -> bool:
    if ignore_id is not None and existing.id == ignore_id:
        return False
    e_start = existing.scheduled_at
    e_end = e_start + timedelta(minutes=existing.duration_minutes)
    return start < e_end and e_start < end


def _check_conflicts(mentor: Mentor, student: User, start, end, ignore_id: int | None = None) -> None:
    for other in mentor.bookings:
        if other.status in ACTIVE and _overlaps(other, start, end, ignore_id):
            raise HTTPException(status_code=409, detail="That time slot is already taken. Pick another time.")
    for other in student.bookings:
        if other.status in ACTIVE and _overlaps(other, start, end, ignore_id):
            raise HTTPException(status_code=409, detail="You already have a session at that time.")


def _resolve_link(mentor: Mentor, student: User, mode: str, start, duration_minutes: int) -> tuple[str | None, str | None]:
    """Returns (meeting_link, location). Raises HTTPException if an online link can't be created."""
    location = mentor.campus_location if mode == "offline" else None
    link = mentor.teams_link if mode == "teams" else None

    if mode == "meet":
        from ..services import zoom_service

        result = zoom_service.create_meeting(
            topic=f"MentorConnect: {mentor.name} & {student.full_name}",
            start_time=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            duration_minutes=duration_minutes,
        )
        link = result["join_url"] or mentor.meet_link  # fall back to the mentor's static link if Zoom fails
        if not link:
            raise HTTPException(
                status_code=502,
                detail=f"Couldn't set up an online meeting right now ({result['error']}). "
                       f"Try again in a minute, or book Teams/on-campus instead.",
            )
    return link, location


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, student: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    mentor = db.get(Mentor, payload.mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found.")
    if payload.scheduled_at <= utcnow() + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Choose a time in the future.")
    if payload.mode not in available_modes(mentor):
        raise HTTPException(
            status_code=422,
            detail=f"{mentor.name} doesn't offer this meeting type yet. Pick one of: {', '.join(available_modes(mentor)) or 'none available'}.",
        )

    ok, reason = fits_within_availability(mentor, payload.scheduled_at, payload.duration_minutes)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)

    end = payload.scheduled_at + timedelta(minutes=payload.duration_minutes)
    _check_conflicts(mentor, student, payload.scheduled_at, end)
    link, location = _resolve_link(mentor, student, payload.mode, payload.scheduled_at, payload.duration_minutes)

    booking = Booking(
        student_id=student.id,
        mentor_id=mentor.id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        mode=payload.mode,
        meeting_link=link,
        location=location,
        topic=payload.topic.strip(),
    )
    db.add(booking)
    db.flush()
    notifications.notify_booking_requested(db, booking)
    db.commit()
    db.refresh(booking)
    return booking_to_dict(booking)


@router.get("/me", response_model=list[BookingOut])
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Students see the sessions they booked; mentors see the sessions booked with them."""
    if user.role == "mentor":
        if not user.mentor_profile:
            return []
        stmt = select(Booking).where(Booking.mentor_id == user.mentor_profile.id)
    else:
        stmt = select(Booking).where(Booking.student_id == user.id)
    rows = list(db.scalars(stmt.order_by(Booking.scheduled_at.desc())))

    if user.role == "mentor":
        _notify_overdue_confirmations(db, rows)

    return [booking_to_dict(b) for b in rows]


def _notify_overdue_confirmations(db: Session, bookings: list[Booking]) -> None:
    """Option A completion-detection (see conversation): no webhook, so nothing truly *knows* a
    call ended -- instead, the moment a mentor's confirmed session's scheduled end time has
    passed, we nudge them (once) to confirm it happened. Purely a reminder; completion is still
    a normal PATCH .../status call underneath, same as always."""
    from ..models.notification import Notification

    now = utcnow()
    changed = False
    for b in bookings:
        if b.status != "confirmed":
            continue
        if b.scheduled_at + timedelta(minutes=b.duration_minutes) > now:
            continue  # hasn't ended yet
        already = db.scalar(
            select(Notification).where(
                Notification.booking_id == b.id,
                Notification.type == "booking_awaiting_confirmation",
            )
        )
        if already:
            continue
        notifications.notify_awaiting_confirmation(db, b)
        changed = True
    if changed:
        db.commit()


@router.patch("/{booking_id}/status", response_model=BookingOut)
def update_status(booking_id: int, payload: BookingStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    is_mentor = user.role == "mentor" and user.mentor_profile is not None and booking.mentor_id == user.mentor_profile.id
    is_student = user.role == "student" and booking.student_id == user.id
    if not (is_mentor or is_student):
        raise HTTPException(status_code=403, detail="You can't change this booking.")

    new, old = payload.status, booking.status
    if old in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"This session is already {old}.")

    if new == "cancelled":
        if not payload.reason or not payload.reason.strip():
            raise HTTPException(status_code=422, detail="A reason is required when cancelling a session.")
        booking.status = "cancelled"
        booking.cancelled_by = "mentor" if is_mentor else "student"
        booking.cancellation_reason = payload.reason.strip()
        db.flush()
        notifications.notify_booking_cancelled(db, booking, booking.cancelled_by)
    elif not is_mentor:
        raise HTTPException(status_code=403, detail="Only the mentor can confirm or complete a session.")
    elif new == "confirmed":
        if old != "pending":
            raise HTTPException(status_code=409, detail="Only pending sessions can be confirmed.")
        booking.status = "confirmed"
        db.flush()
        notifications.notify_booking_confirmed(db, booking)
    elif new == "completed":
        if old != "confirmed":
            raise HTTPException(status_code=409, detail="Confirm the session before marking it completed.")
        if booking.scheduled_at > utcnow():
            raise HTTPException(status_code=409, detail="This session hasn't started yet.")
        booking.status = "completed"
        db.flush()
        notifications.notify_booking_completed(db, booking)

    db.commit()
    db.refresh(booking)
    return booking_to_dict(booking)


@router.patch("/{booking_id}/reschedule", response_model=BookingOut)
def reschedule_booking(booking_id: int, payload: RescheduleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    is_mentor = user.role == "mentor" and user.mentor_profile is not None and booking.mentor_id == user.mentor_profile.id
    is_student = user.role == "student" and booking.student_id == user.id
    if not (is_mentor or is_student):
        raise HTTPException(status_code=403, detail="You can't change this booking.")
    if booking.status not in ACTIVE:
        raise HTTPException(status_code=409, detail=f"This session is {booking.status} and can't be rescheduled.")
    if payload.scheduled_at <= utcnow() + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Choose a time in the future.")

    mentor = booking.mentor
    ok, reason = fits_within_availability(mentor, payload.scheduled_at, booking.duration_minutes)
    if not ok:
        raise HTTPException(status_code=422, detail=reason)

    end = payload.scheduled_at + timedelta(minutes=booking.duration_minutes)
    _check_conflicts(mentor, booking.student, payload.scheduled_at, end, ignore_id=booking.id)

    # Re-resolve the online link for the new time (a Zoom meeting is tied to a specific start time).
    link, location = _resolve_link(mentor, booking.student, booking.mode, payload.scheduled_at, booking.duration_minutes)

    booking.previous_scheduled_at = booking.scheduled_at
    booking.scheduled_at = payload.scheduled_at
    booking.meeting_link = link
    booking.location = location
    booking.rescheduled_by = "mentor" if is_mentor else "student"
    booking.reschedule_reason = payload.reason.strip()
    booking.reschedule_count = (booking.reschedule_count or 0) + 1
    # The other party needs to re-confirm the new time, unless it hadn't been confirmed yet.
    booking.status = "pending"
    db.flush()
    notifications.notify_booking_rescheduled(db, booking, booking.rescheduled_by)
    db.commit()
    db.refresh(booking)
    return booking_to_dict(booking)


@router.post("/{booking_id}/review", response_model=BookingOut)
def review(booking_id: int, payload: ReviewIn, student: User = Depends(require_role("student")), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking or booking.student_id != student.id:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != "completed":
        raise HTTPException(status_code=409, detail="You can rate a session once the mentor has marked it completed.")
    if booking.rating is not None:
        raise HTTPException(status_code=409, detail="You've already rated this session.")
    booking.rating = payload.rating
    booking.feedback = (payload.feedback or "").strip() or None
    db.commit()
    db.refresh(booking)
    return booking_to_dict(booking)

@router.patch("/{booking_id}/location", response_model=BookingOut)
def update_location(booking_id: int, payload: LocationUpdateIn, mentor_user: User = Depends(require_role("mentor")), db: Session = Depends(get_db)):
    """The actual room for an on-campus session often isn't known until closer to the date, and
    can differ from one session to the next -- so this is set per-booking, not just inherited
    from the mentor's profile default. Editable any time before the session is cancelled."""
    booking = db.get(Booking, booking_id)
    if not booking or not mentor_user.mentor_profile or booking.mentor_id != mentor_user.mentor_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.mode != "offline":
        raise HTTPException(status_code=422, detail="This session isn't on-campus, so it has no room to set.")
    if booking.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=409, detail="This session is no longer upcoming.")

    changed = booking.location != payload.location
    booking.location = payload.location
    db.commit()
    db.refresh(booking)
    if changed:
        notifications.notify_location_changed(db, booking)
        db.commit()
    return booking_to_dict(booking)