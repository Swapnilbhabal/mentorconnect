from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class StudentProfile(Base):
    """Academic details for a student account, filled in at registration and editable after.

    Every field is nullable at the database level -- the conditional "this is required"
    business rules (e.g. institute_name required once institute_type is set) are enforced by
    the Pydantic schemas, not here, so the table itself never blocks a partial/incomplete save.
    """

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    institute_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # school | college | university | other
    institute_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    roll_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    program_level: Mapped[str | None] = mapped_column(String(20), nullable=True)  # UG | PG
    year_of_study: Mapped[str | None] = mapped_column(String(20), nullable=True)  # free text, e.g. "2nd Year"
    branch: Mapped[str | None] = mapped_column(String(120), nullable=True)  # e.g. "Computer Science"

    user = relationship("User", back_populates="student_profile")