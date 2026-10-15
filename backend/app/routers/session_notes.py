"""SRS 4.5 (Automated Session Intelligence) and 4.6 (Mentor Memory System)."""
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..models.booking import Booking
from ..models.session_note import SessionNote
from ..models.user import User
from ..schemas.session_note import SessionNoteIn, SessionNoteOut, StudentMemoryOut
from ..security import get_current_user, require_role
from ..services import notifications
from ..services.session_notes_service import generate_session_notes

router = APIRouter(tags=["Session Notes"])


def _note_to_dict(n: SessionNote) -> dict:
    return {
        "id": n.id,
        "booking_id": n.booking_id,
        "strengths": json.loads(n.strengths or "[]"),
        "weaknesses": json.loads(n.weaknesses or "[]"),
        "action_items": json.loads(n.action_items or "[]"),
        "source": n.source,
        "error_message": n.error_message,
        "created_at": n.created_at,
    }


@router.post("/bookings/{booking_id}/notes", response_model=SessionNoteOut, status_code=status.HTTP_201_CREATED)
def add_session_notes(booking_id: int, payload: SessionNoteIn, user: User = Depends(require_role("mentor")), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking or not user.mentor_profile or booking.mentor_id != user.mentor_profile.id:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != "completed":
        raise HTTPException(status_code=409, detail="Session notes can only be added once the session is marked completed.")
    if db.scalar(select(SessionNote).where(SessionNote.booking_id == booking_id)):
        raise HTTPException(status_code=409, detail="Notes have already been added for this session.")

    result = generate_session_notes(payload.feedback, booking.topic or "General mentoring session")
    if result["invalid_reason"]:
        raise HTTPException(status_code=422, detail=result["invalid_reason"])

    now = utcnow()
    action_items = [
        {"item": a["item"], "deadline": (now + timedelta(days=a.get("days", 7))).isoformat()}
        for a in result["action_items"]
    ]
    note = SessionNote(
        booking_id=booking_id,
        student_id=booking.student_id,
        mentor_id=booking.mentor_id,
        raw_feedback=payload.feedback,
        strengths=json.dumps(result["strengths"]),
        weaknesses=json.dumps(result["weaknesses"]),
        action_items=json.dumps(action_items),
        source=result["source"],
        error_message=result["error"],
    )
    db.add(note)
    db.flush()
    notifications.notify_session_notes_ready(db, note)
    db.commit()
    db.refresh(note)
    return _note_to_dict(note)


@router.get("/bookings/{booking_id}/notes", response_model=SessionNoteOut)
def get_session_notes(booking_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    note = db.scalar(select(SessionNote).where(SessionNote.booking_id == booking_id))
    if not note:
        raise HTTPException(status_code=404, detail="No notes for this session yet.")
    is_mentor = user.mentor_profile is not None and note.mentor_id == user.mentor_profile.id
    is_student = note.student_id == user.id
    if not (is_mentor or is_student):
        raise HTTPException(status_code=403, detail="You can't view these notes.")
    return _note_to_dict(note)


@router.get("/mentors/students/{student_id}/memory", response_model=StudentMemoryOut)
def student_memory(student_id: int, user: User = Depends(require_role("mentor")), db: Session = Depends(get_db)):
    """Redesigned "remembers this student" feature: a mentor with a confirmed upcoming booking
    with a student sees THEIR OWN past session notes with that specific student -- never notes
    from any other mentor. This is for continuity ("you're the one working on the IoT project,
    how did the sensor calibration go?"), not a cross-mentor profile of the student. If this is
    the first time this mentor has met this student, `sessions` is simply empty -- that's a
    normal, expected result, not an error."""
    if not user.mentor_profile:
        raise HTTPException(status_code=404, detail="No mentor profile is linked to this account.")

    has_upcoming = db.scalar(
        select(Booking).where(
            Booking.student_id == student_id,
            Booking.mentor_id == user.mentor_profile.id,
            Booking.status == "confirmed",
            Booking.scheduled_at > utcnow(),
        )
    )
    if not has_upcoming:
        raise HTTPException(
            status_code=403,
            detail="You can view your past sessions with a student once you have a confirmed, upcoming session with them.",
        )

    student = db.get(User, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    notes = db.scalars(
        select(SessionNote)
        .where(SessionNote.student_id == student_id, SessionNote.mentor_id == user.mentor_profile.id)
        .order_by(SessionNote.created_at.desc())
    )
    sessions = [
        {
            "session_date": n.created_at,
            "topic": n.booking.topic or "Mentoring session",
            "strengths": json.loads(n.strengths or "[]"),
            "weaknesses": json.loads(n.weaknesses or "[]"),
            "action_items": json.loads(n.action_items or "[]"),
        }
        for n in notes
    ]

    return {"student_name": student.full_name, "sessions": sessions}