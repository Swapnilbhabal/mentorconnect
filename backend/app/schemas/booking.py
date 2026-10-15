from typing import Literal

from pydantic import BaseModel, Field

from .common import UTCDateTime
from .mentor import Mode
from .student import StudentProfileOut


class BookingCreate(BaseModel):
    mentor_id: int
    scheduled_at: UTCDateTime
    duration_minutes: Literal[15, 30, 45, 60] = 30
    mode: Mode
    topic: str = Field(default="", max_length=300)


class BookingStatusUpdate(BaseModel):
    status: Literal["confirmed", "completed", "cancelled"]
    # Required when status == "cancelled" (SRS-adjacent request: always explain a cancellation).
    reason: str | None = Field(default=None, max_length=500)


class RescheduleIn(BaseModel):
    scheduled_at: UTCDateTime
    reason: str = Field(min_length=1, max_length=500, description="Required: why this session is moving")


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    feedback: str | None = Field(default=None, max_length=1000)

class LocationUpdateIn(BaseModel):
    """Lets a mentor set/change the room for THIS one on-campus session -- the actual room
    often varies session to session, so this isn't tied to the mentor's profile default."""
    location: str = Field(min_length=1, max_length=200)


class BookingOut(BaseModel):
    id: int
    mentor_id: int
    mentor_name: str
    mentor_avatar_url: str | None = None
    student_id: int
    student_name: str
    student_academic: StudentProfileOut | None = None
    scheduled_at: UTCDateTime
    duration_minutes: int
    mode: str
    meeting_link: str | None = None
    location: str | None = None
    topic: str
    status: str
    cancelled_by: str | None = None
    cancellation_reason: str | None = None
    rescheduled_by: str | None = None
    reschedule_reason: str | None = None
    previous_scheduled_at: UTCDateTime | None = None
    reschedule_count: int = 0
    rating: int | None = None
    feedback: str | None = None
    has_notes: bool = False  # true once the mentor has added structured session notes


# --- Notifications ---

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: str
    booking_id: int | None = None
    is_read: bool
    created_at: UTCDateTime