"""Weekly availability enforcement (SRS REQ-5-1).

A mentor with no AvailabilitySlot rows has not opted in yet -- bookings for them are
unrestricted (keeps every previously-seeded/created mentor working exactly as before).
Once a mentor defines at least one slot, every booking must fit entirely inside one slot.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ..models.mentor import Mentor

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def fits_within_availability(mentor: Mentor, start: datetime, duration_minutes: int) -> tuple[bool, str | None]:
    """Returns (ok, error_message). error_message is None when ok is True.
    Only checks a single day: a session that would cross midnight is rejected with a clear
    message rather than silently checking the wrong day."""
    slots = mentor.availability_slots
    if not slots:
        return True, None  # mentor hasn't opted into structured slots -- unrestricted

    end = start + timedelta(minutes=duration_minutes)
    if end.date() != start.date():
        return False, "Sessions can't span midnight. Pick a time that ends the same day it starts."

    weekday = start.weekday()
    start_min = start.hour * 60 + start.minute
    end_min = end.hour * 60 + end.minute

    day_slots = [s for s in slots if s.weekday == weekday]
    for s in day_slots:
        if _minutes(s.start_time) <= start_min and end_min <= _minutes(s.end_time):
            return True, None

    if not day_slots:
        return False, f"{mentor.name} has no available slots on {WEEKDAY_NAMES[weekday]}s."

    windows = ", ".join(f"{s.start_time}-{s.end_time}" for s in sorted(day_slots, key=lambda s: s.start_time))
    return False, f"That time is outside {mentor.name}'s available slots for {WEEKDAY_NAMES[weekday]} ({windows} UTC)."