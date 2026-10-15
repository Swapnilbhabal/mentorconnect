from typing import Literal

from pydantic import BaseModel, Field

from .common import UTCDateTime


class GenerateIn(BaseModel):
    goal: str = Field(min_length=2, max_length=120, description="e.g. 'Senior AI Agent Developer'")
    replace_id: int | None = Field(default=None, description="Delete this roadmap once the new one is saved (retry flow)")


class MilestoneOut(BaseModel):
    id: int
    position: int
    title: str
    description: str
    topics: list[str]
    duration_weeks: int | None = None
    status: str


class MilestoneUpdate(BaseModel):
    status: Literal["pending", "in_progress", "completed"]


class RoadmapOut(BaseModel):
    id: int
    goal: str
    source: str  # "gemini" or "template"
    error_message: str | None = None
    created_at: UTCDateTime
    milestones: list[MilestoneOut]
    progress: int  # 0-100, share of completed milestones
