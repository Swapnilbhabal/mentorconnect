"""Mentor rating statistics.

A plain, transparent average of student ratings (1-5 stars) -- no hidden formula, no weighting
against completion rate. What you see is exactly what students typed in.

- Ratings from before the platform (the "base_rating_*" columns) act as a prior, so a brand-new
  platform doesn't wipe out a professor's track record.
- Mentors with no ratings at all get `rating_avg = None` (shown as "New" in the UI).
- completion_rate is still tracked (session history is useful context) but no longer feeds into
  any single blended "score" -- it's shown as its own plain stat.
"""
from __future__ import annotations

from ..models.mentor import Mentor


def mentor_stats(mentor: Mentor) -> dict:
    ratings = [b.rating for b in mentor.bookings if b.rating]
    completed = sum(1 for b in mentor.bookings if b.status == "completed")
    mentor_cancelled = sum(1 for b in mentor.bookings if b.status == "cancelled" and b.cancelled_by == "mentor")

    rating_count = mentor.base_rating_count + len(ratings)
    rating_avg = None
    if rating_count:
        rating_avg = (mentor.base_rating_avg * mentor.base_rating_count + sum(ratings)) / rating_count

    sessions_completed = mentor.base_sessions_completed + completed
    sessions_total = mentor.base_sessions_total + completed + mentor_cancelled
    completion_rate = sessions_completed / sessions_total if sessions_total else None

    return {
        "rating_avg": round(rating_avg, 2) if rating_avg is not None else None,
        "rating_count": rating_count,
        "sessions_completed": sessions_completed,
        "completion_rate": round(completion_rate, 3) if completion_rate is not None else None,
    }