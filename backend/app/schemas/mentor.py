from typing import Literal

from pydantic import BaseModel, Field

from .common import UTCDateTime
from .user import InstituteType

Mode = Literal["meet", "teams", "offline"]


class MentorCreate(BaseModel):
    """Body for POST /mentors/. `user_id` is optional: leave it out to create a profile with no login."""

    name: str = Field(min_length=2, max_length=120)
    expertise: str = Field(default="", max_length=500, description="Comma separated, e.g. 'FastAPI, React'")
    bio: str = Field(default="", max_length=2000)
    long_bio: str | None = Field(default=None, max_length=4000, description="Full version shown only on the detail page")
    user_id: int | None = None
    department: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    years_experience: int = Field(default=0, ge=0, le=60)
    meet_link: str | None = Field(default=None, max_length=500)
    teams_link: str | None = Field(default=None, max_length=500)
    campus_location: str | None = Field(default=None, max_length=200)
    availability: str | None = Field(default=None, max_length=200)
    institute_type: InstituteType | None = None
    institute_name: str | None = Field(default=None, max_length=200)
    institute_unique_id: str | None = Field(default=None, max_length=50)


class MentorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    expertise: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)
    long_bio: str | None = Field(default=None, max_length=4000)
    department: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=500)
    years_experience: int | None = Field(default=None, ge=0, le=60)
    meet_link: str | None = Field(default=None, max_length=500)
    teams_link: str | None = Field(default=None, max_length=500)
    campus_location: str | None = Field(default=None, max_length=200)
    availability: str | None = Field(default=None, max_length=200)
    institute_type: InstituteType | None = None
    institute_name: str | None = Field(default=None, max_length=200)
    institute_unique_id: str | None = Field(default=None, max_length=50)


class MentorOut(BaseModel):
    id: int
    user_id: int | None = None
    name: str
    expertise: str
    expertise_list: list[str]
    bio: str
    long_bio: str | None = None
    department: str | None = None
    avatar_url: str | None = None
    years_experience: int = 0
    available_modes: list[str]
    meet_link: str | None = None
    teams_link: str | None = None
    campus_location: str | None = None
    availability: str | None = None
    # Live statistics: a plain average of student ratings, no blended/hidden formula.
    rating_avg: float | None = None  # 0-5, None until the mentor has at least one rating
    rating_count: int = 0
    sessions_completed: int = 0
    completion_rate: float | None = None
    # Verification (SRS 4.2). platform_verified is the single badge shown to students,
    # true regardless of which verification_path was used.
    platform_verified: bool = False
    verification_status: str = "unverified"
    # Structured weekly slots (SRS REQ-5-1). Empty list = mentor hasn't opted in; bookings
    # are then unrestricted. Non-empty = every booking must fall inside one of these.
    slots: list["SlotOut"] = []
    # Institute affiliation (SRS point 3). institute_unique_id is shown to admins reviewing
    # this mentor's verification request, to cross-check against their uploaded document.
    institute_type: str | None = None
    institute_type_label: str | None = None
    institute_name: str | None = None
    institute_unique_id: str | None = None


# --- Weekly availability slots (SRS REQ-5-1) ---

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


class SlotIn(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=Monday ... 6=Sunday")
    start_time: str = Field(pattern=TIME_PATTERN, description="24h HH:MM, UTC")
    end_time: str = Field(pattern=TIME_PATTERN, description="24h HH:MM, UTC")


class SlotsReplaceIn(BaseModel):
    slots: list[SlotIn] = Field(max_length=50)


class SlotOut(BaseModel):
    id: int
    weekday: int
    weekday_name: str
    start_time: str
    end_time: str

class ReviewOut(BaseModel):
    """A single completed, rated session shown on a mentor's public profile. Deliberately
    carries no student identity -- same privacy stance as the busy-ranges endpoint -- so a
    student's free-text feedback is never tied to their name for other students to browse."""
    rating: int
    feedback: str | None = None
    session_date: UTCDateTime

class BusyRangeOut(BaseModel):
    """One already-occupied time range for a mentor (an active booking's start/end in UTC).
    Deliberately carries no information about WHO booked it -- just that the slot is taken,
    the same way a ticket-booking seat map shows a seat as unavailable without naming the
    person sitting there."""
    start: UTCDateTime
    end: UTCDateTime


MentorOut.model_rebuild()


VerificationPath = Literal["industry", "academic", "coaching", "community"]

VERIFICATION_PATH_LABELS = {
    "industry": "Industry Professional",
    "academic": "Academic Mentor",
    "coaching": "Coaching Teacher",
    "community": "Community Mentor",
}


class VerificationOut(BaseModel):
    status: str  # unverified | pending | verified | rejected
    path: str | None = None
    path_label: str | None = None
    document_name: str | None = None
    rejection_reason: str | None = None
    submitted_at: str | None = None
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    platform_verified: bool = False


class VerificationReviewIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000, description="Required when rejecting")


class VerificationQueueItem(BaseModel):
    mentor_id: int
    name: str
    department: str | None = None
    expertise: str
    path: str | None = None
    path_label: str | None = None
    document_name: str | None = None
    status: str
    submitted_at: str | None = None
    # Shown so an admin can cross-check the mentor's claimed institute ID against their document.
    institute_type_label: str | None = None
    institute_name: str | None = None
    institute_unique_id: str | None = None