from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    goal: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(20), default="gemini")  # "gemini" | "template"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # exact error when AI failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user = relationship("User", back_populates="roadmaps")
    milestones = relationship(
        "Milestone", back_populates="roadmap", cascade="all, delete-orphan", order_by="Milestone.position"
    )


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(primary_key=True)
    roadmap_id: Mapped[int] = mapped_column(ForeignKey("roadmaps.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    topics: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of strings
    duration_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | in_progress | completed

    roadmap = relationship("Roadmap", back_populates="milestones")
