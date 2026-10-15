from pydantic import BaseModel, Field

from .common import UTCDateTime


class SessionNoteIn(BaseModel):
    feedback: str = Field(min_length=3, max_length=3000, description="Quick raw notes -- AI turns these into structured feedback")


class ActionItemOut(BaseModel):
    item: str
    deadline: UTCDateTime


class SessionNoteOut(BaseModel):
    id: int
    booking_id: int
    strengths: list[str]
    weaknesses: list[str]
    action_items: list[ActionItemOut]
    source: str  # "gemini" or "template"
    error_message: str | None = None
    created_at: UTCDateTime


# --- "Remembers this student" (redesigned): same mentor, same student, past sessions only.
# No cross-mentor data is ever involved -- a mentor only ever sees their OWN past notes about
# a student they are about to meet again, nothing any other mentor wrote. ---

class PastSessionNoteOut(BaseModel):
    session_date: UTCDateTime
    topic: str
    strengths: list[str]
    weaknesses: list[str]
    action_items: list[ActionItemOut]


class StudentMemoryOut(BaseModel):
    student_name: str
    sessions: list[PastSessionNoteOut]  # empty = you haven't met this student before