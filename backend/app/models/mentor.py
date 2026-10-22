from sqlalchemy import ForeignKey, Integer, Float, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Mentor(Base):
    __tablename__ = "mentors"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable so a mentor profile can exist without a login (e.g. created through /docs).
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True)

    name: Mapped[str] = mapped_column(String(120), index=True)
    expertise: Mapped[str] = mapped_column(String(500), default="")  # comma separated
    bio: Mapped[str] = mapped_column(Text, default="")  # short, shown on the card list
    long_bio: Mapped[str | None] = mapped_column(Text, nullable=True)  # full version, detail page only
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, default=0)

    # How students can meet this mentor. A mode is offered only when its link/location is filled in.
    meet_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    teams_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    campus_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    availability: Mapped[str | None] = mapped_column(String(200), nullable=True)  # free text, e.g. "Mon-Fri, 4-6 PM"

    # History from before the platform (used as a prior for the effectiveness score)
    base_rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    base_rating_count: Mapped[int] = mapped_column(Integer, default=0)
    base_sessions_completed: Mapped[int] = mapped_column(Integer, default=0)
    base_sessions_total: Mapped[int] = mapped_column(Integer, default=0)
    # Institute affiliation, captured at registration. institute_unique_id is the mentor's own
    # institute-issued ID (e.g. an employee/faculty code like "VITCMPN111") -- required whenever
    # institute_type is school/college/university, so an admin can cross-check it against the
    # uploaded verification document instead of relying on the document alone.
    institute_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # school | college | university | other
    institute_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    institute_unique_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Multi-path verification (SRS 4.2). status: unverified | pending | verified | rejected.
    # path is one of: industry | academic | coaching | community -- shown internally, but the
    # badge shown to students is the same "Platform Verified" regardless of which path was used.
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")
    verification_path: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verification_document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_document_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    verification_document_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verification_rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_submitted_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verification_reviewed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verification_reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)

    user = relationship("User", back_populates="mentor_profile")
    bookings = relationship("Booking", back_populates="mentor", cascade="all, delete-orphan")
    availability_slots = relationship("AvailabilitySlot", back_populates="mentor", cascade="all, delete-orphan")
