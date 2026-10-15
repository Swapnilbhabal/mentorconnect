from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class AvailabilitySlot(Base):
    """One recurring weekly window a mentor is bookable in, e.g. 'Monday 16:00-18:00'.

    All times are naive UTC, same convention as the rest of the app (see Booking.scheduled_at).
    A mentor with zero rows here has NOT opted into enforcement yet -- bookings for them fall
    back to the old unrestricted behavior, so existing/seeded mentors aren't broken by this
    feature landing. Once a mentor adds at least one slot, every booking with them must fall
    inside one of their slots.
    """

    __tablename__ = "availability_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Monday ... 6=Sunday (Python's date.weekday())
    start_time: Mapped[str] = mapped_column(String(5))  # "HH:MM", 24h, UTC
    end_time: Mapped[str] = mapped_column(String(5))  # "HH:MM", 24h, UTC

    mentor = relationship("Mentor", back_populates="availability_slots")