"""Turn ORM objects into the dictionaries the response schemas expect."""
import json

from ..models.booking import Booking
from ..models.mentor import Mentor
from ..models.roadmap import Roadmap
from ..models.student import StudentProfile
from ..models.user import User
from ..schemas.user import INSTITUTE_TYPE_LABELS
from .scoring import mentor_stats

VERIFICATION_PATH_LABELS = {
    "industry": "Industry Professional",
    "academic": "Academic Mentor",
    "coaching": "Coaching Teacher",
    "community": "Community Mentor",
}


def _split(value: str | None) -> list[str]:
    return [p.strip() for p in (value or "").split(",") if p.strip()]


def available_modes(m: Mentor) -> list[str]:
    from ..config import settings  # local import avoids a circular import at module load time

    modes = []
    # "meet" is Zoom-backed: available once the platform's Zoom account is configured,
    # or as a fallback if this mentor still has their own static link saved.
    if settings.ZOOM_ENABLED or m.meet_link:
        modes.append("meet")
    if m.teams_link:
        modes.append("teams")
    # "offline" is always bookable, same spirit as "meet": the room doesn't need to be known
    # up front. If the mentor hasn't set a default (or a specific one for this booking) yet,
    # the student just sees "room to be confirmed" until the mentor fills it in.
    modes.append("offline")
    return modes


def mentor_to_dict(m: Mentor) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "name": m.name,
        "expertise": m.expertise or "",
        "expertise_list": _split(m.expertise),
        "bio": m.bio or "",
        "long_bio": m.long_bio,
        "department": m.department,
        "avatar_url": m.avatar_url,
        "years_experience": m.years_experience or 0,
        "available_modes": available_modes(m),
        "meet_link": m.meet_link,
        "teams_link": m.teams_link,
        "campus_location": m.campus_location,
        "availability": m.availability,
        "platform_verified": m.verification_status == "verified",
        "verification_status": m.verification_status or "unverified",
        "slots": [slot_to_dict(s) for s in m.availability_slots],
        "institute_type": m.institute_type,
        "institute_type_label": INSTITUTE_TYPE_LABELS.get(m.institute_type or "", None),
        "institute_name": m.institute_name,
        "institute_unique_id": m.institute_unique_id,
        **mentor_stats(m),
    }


def verification_to_dict(m: Mentor) -> dict:
    return {
        "status": m.verification_status or "unverified",
        "path": m.verification_path,
        "path_label": VERIFICATION_PATH_LABELS.get(m.verification_path or "", None),
        "document_name": m.verification_document_name,
        "rejection_reason": m.verification_rejection_reason,
        "submitted_at": m.verification_submitted_at,
        "reviewed_at": m.verification_reviewed_at,
        "reviewed_by": m.verification_reviewed_by,
        "platform_verified": m.verification_status == "verified",
    }


def verification_queue_item(m: Mentor) -> dict:
    return {
        "mentor_id": m.id,
        "name": m.name,
        "department": m.department,
        "expertise": m.expertise or "",
        "path": m.verification_path,
        "path_label": VERIFICATION_PATH_LABELS.get(m.verification_path or "", None),
        "document_name": m.verification_document_name,
        "status": m.verification_status or "unverified",
        "submitted_at": m.verification_submitted_at,
        "institute_type_label": INSTITUTE_TYPE_LABELS.get(m.institute_type or "", None),
        "institute_name": m.institute_name,
        "institute_unique_id": m.institute_unique_id,
    }


def student_profile_to_dict(s: StudentProfile | None) -> dict:
    if s is None:
        return {
            "institute_type": None, "institute_type_label": None, "institute_name": None,
            "roll_number": None, "program_level": None, "year_of_study": None, "branch": None,
        }
    return {
        "institute_type": s.institute_type,
        "institute_type_label": INSTITUTE_TYPE_LABELS.get(s.institute_type or "", None),
        "institute_name": s.institute_name,
        "roll_number": s.roll_number,
        "program_level": s.program_level,
        "year_of_study": s.year_of_study,
        "branch": s.branch,
    }


def user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "avatar_url": u.avatar_url,
        "mentor_id": u.mentor_profile.id if u.mentor_profile else None,
    }


def milestone_to_dict(ms) -> dict:
    return {
        "id": ms.id,
        "position": ms.position,
        "title": ms.title,
        "description": ms.description,
        "topics": json.loads(ms.topics or "[]"),
        "duration_weeks": ms.duration_weeks,
        "status": ms.status,
    }


def roadmap_to_dict(r: Roadmap) -> dict:
    milestones = [milestone_to_dict(ms) for ms in r.milestones]
    done = sum(1 for ms in milestones if ms["status"] == "completed")
    return {
        "id": r.id,
        "goal": r.goal,
        "source": r.source,
        "error_message": r.error_message,
        "created_at": r.created_at,
        "milestones": milestones,
        "progress": round(100 * done / len(milestones)) if milestones else 0,
    }


def booking_to_dict(b: Booking) -> dict:
    return {
        "id": b.id,
        "mentor_id": b.mentor_id,
        "mentor_name": b.mentor.name,
        "mentor_avatar_url": b.mentor.avatar_url,
        "student_id": b.student_id,
        "student_name": b.student.full_name,
        # Academic context for the mentor actually handling this booking (REQ: mentor sees
        # more than just a name, so they can guide the student appropriately). Safe to include
        # unconditionally -- every caller of this function already only sees bookings they are
        # the mentor or student of, enforced by the endpoint, same as everywhere else in the app.
        "student_academic": student_profile_to_dict(b.student.student_profile),
        "scheduled_at": b.scheduled_at,
        "duration_minutes": b.duration_minutes,
        "mode": b.mode,
        "meeting_link": b.meeting_link,
        "location": b.location,
        "topic": b.topic or "",
        "status": b.status,
        "cancelled_by": b.cancelled_by,
        "cancellation_reason": b.cancellation_reason,
        "rescheduled_by": b.rescheduled_by,
        "reschedule_reason": b.reschedule_reason,
        "previous_scheduled_at": b.previous_scheduled_at,
        "reschedule_count": b.reschedule_count or 0,
        "rating": b.rating,
        "feedback": b.feedback,
        "has_notes": b.session_note is not None,
    }


WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def slot_to_dict(s) -> dict:
    return {
        "id": s.id,
        "weekday": s.weekday,
        "weekday_name": WEEKDAY_NAMES[s.weekday],
        "start_time": s.start_time,
        "end_time": s.end_time,
    }


def notification_to_dict(n) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "booking_id": n.booking_id,
        "is_read": n.is_read,
        "created_at": n.created_at,
    }