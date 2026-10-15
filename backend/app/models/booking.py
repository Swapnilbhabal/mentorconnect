from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id"), index=True)

    scheduled_at: Mapped[datetime] = mapped_column(DateTime)  # naive UTC
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    mode: Mapped[str] = mapped_column(String(20))  # meet | teams | offline
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    topic: Mapped[str] = mapped_column(String(300), default="")

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | confirmed | completed | cancelled
    cancelled_by: Mapped[str | None] = mapped_column(String(20), nullable=True)  # student | mentor
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reschedule history: only the most recent reschedule is kept (fields overwritten each time).
    rescheduled_by: Mapped[str | None] = mapped_column(String(20), nullable=True)  # student | mentor
    reschedule_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reschedule_count: Mapped[int] = mapped_column(Integer, default=0)

    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5, left by the student
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    student = relationship("User", back_populates="bookings")
    mentor = relationship("Mentor", back_populates="bookings")
    session_note = relationship("SessionNote", uselist=False, viewonly=True)