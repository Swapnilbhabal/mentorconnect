from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow


class SessionNote(Base):
    """One mentor's post-session feedback for one booking (SRS 4.5), AI-structured into
    strengths / weaknesses / action items with deadlines. Feeds "remembers this student":
    when the SAME mentor has a confirmed upcoming session with this student again, they see
    their own past notes -- never another mentor's."""

    __tablename__ = "session_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id"), index=True)

    raw_feedback: Mapped[str] = mapped_column(Text)  # exactly what the mentor typed
    strengths: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    weaknesses: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    action_items: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[{"item", "deadline"}]

    source: Mapped[str] = mapped_column(String(20), default="gemini")  # "gemini" | "template"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # exact error when AI failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    booking = relationship("Booking")
    student = relationship("User")
    mentor = relationship("Mentor")