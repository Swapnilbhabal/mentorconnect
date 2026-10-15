"""In-app notifications for the booking lifecycle (SRS 'MAIN point': notify both sides).

Each call here just inserts a row -- it never raises, so a notification hiccup never breaks
the booking action itself. The frontend polls GET /notifications/me for new ones.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..models.booking import Booking
from ..models.notification import Notification


def _add(db: Session, user_id: int, type_: str, title: str, body: str, booking_id: int) -> None:
    db.add(Notification(user_id=user_id, type=type_, title=title, body=body, booking_id=booking_id))


def notify_booking_requested(db: Session, b: Booking) -> None:
    _add(
        db,
        user_id=b.mentor.user_id,
        type_="booking_requested",
        title=f"New session request from {b.student.full_name}",
        body=f"{b.topic or 'A session'} requested for {b.scheduled_at:%a %d %b, %H:%M} UTC.",
        booking_id=b.id,
    ) if b.mentor.user_id else None


def notify_booking_confirmed(db: Session, b: Booking) -> None:
    _add(
        db,
        user_id=b.student_id,
        type_="booking_confirmed",
        title=f"{b.mentor.name} confirmed your session",
        body=f"Scheduled for {b.scheduled_at:%a %d %b, %H:%M} UTC.",
        booking_id=b.id,
    )


def notify_booking_completed(db: Session, b: Booking) -> None:
    _add(
        db,
        user_id=b.student_id,
        type_="booking_completed",
        title=f"{b.mentor.name} marked your session as done",
        body="You can now rate the session.",
        booking_id=b.id,
    )


def notify_booking_cancelled(db: Session, b: Booking, cancelled_by_role: str) -> None:
    """Notifies whichever side did NOT cancel."""
    if cancelled_by_role == "student":
        if not b.mentor.user_id:
            return
        recipient, actor = b.mentor.user_id, b.student.full_name
    else:
        recipient, actor = b.student_id, b.mentor.name
    _add(
        db,
        user_id=recipient,
        type_="booking_cancelled",
        title=f"{actor} cancelled the session",
        body=b.cancellation_reason or "No reason given.",
        booking_id=b.id,
    )


def notify_booking_rescheduled(db: Session, b: Booking, rescheduled_by_role: str) -> None:
    """Notifies whichever side did NOT initiate the reschedule."""
    if rescheduled_by_role == "student":
        if not b.mentor.user_id:
            return
        recipient, actor = b.mentor.user_id, b.student.full_name
    else:
        recipient, actor = b.student_id, b.mentor.name
    _add(
        db,
        user_id=recipient,
        type_="booking_rescheduled",
        title=f"{actor} rescheduled the session",
        body=f"New time: {b.scheduled_at:%a %d %b, %H:%M} UTC. Reason: {b.reschedule_reason}",
        booking_id=b.id,
    )

def notify_session_notes_ready(db: Session, note) -> None:
    _add(
        db,
        user_id=note.student_id,
        type_="session_notes_ready",
        title=f"{note.mentor.name} added notes from your session",
        body="Strengths, areas to work on and action items are ready to view.",
        booking_id=note.booking_id,
    )


def notify_location_changed(db: Session, b: Booking) -> None:
    _add(
        db,
        user_id=b.student_id,
        type_="location_changed",
        title=f"Room updated for your session with {b.mentor.name}",
        body=f"New location: {b.location}.",
        booking_id=b.id,
    )
def notify_awaiting_confirmation(db: Session, b: Booking) -> None:
    """Nudges the mentor once a confirmed session's scheduled end time has passed, in case they
    forgot to mark it completed (which is what unlocks the student's ability to rate it).
    Manual/automatic-webhook completion both still work exactly the same afterward -- this is
    purely a reminder, not a status change."""
    if not b.mentor.user_id:
        return
    _add(
        db,
        user_id=b.mentor.user_id,
        type_="booking_awaiting_confirmation",
        title=f"Did your session with {b.student.full_name} happen?",
        body="Its scheduled time has passed. Mark it completed so they can leave a rating.",
        booking_id=b.id,
    )