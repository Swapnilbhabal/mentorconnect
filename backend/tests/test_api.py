"""End-to-end API tests. Run from the backend folder:  pytest -q
Uses a throw-away SQLite file and a fake Gemini, so no API key or internet is needed.

Most tests register their own throwaway students/mentors via the real API rather than relying
on specific seeded names, so no test depends on a particular real faculty member existing.
"""
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.services import ai_service  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs lifespan -> creates tables, migrates, seeds
        yield c


def auth(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def future(hours=48):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


# ---------- Seeding, search, filters ----------

def test_seed_and_mentor_filters(client):
    mentors = client.get("/mentors/").json()
    assert len(mentors) >= 15  # the real VIT faculty roster
    assert all(m["avatar_url"].startswith("https://ui-avatars.com") for m in mentors)
    assert all(m["institute_name"] for m in mentors)  # real institute, never fabricated per-person data
    assert client.get("/mentors/?q=zzzz-nothing-matches").json() == []
    # "offline" is always bookable, same spirit as "meet" being Zoom-backed
    assert all("offline" in m["available_modes"] for m in mentors)


def test_create_mentor_profile_without_user_id_works(client):
    """Regression: /docs used to return 422 'user_id field required'."""
    body = {"name": "Dr. Test Mentor", "expertise": "FastAPI, React", "bio": "Testing."}
    r = client.post("/mentors/", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["rating_avg"] is None  # brand new mentor, no fabricated rating


def test_open_mentor_creation_can_be_disabled(client, monkeypatch):
    from app.routers import mentors as mentors_router
    monkeypatch.setattr(mentors_router.settings, "ALLOW_OPEN_MENTOR_CREATION", False)
    r = client.post("/mentors/", json={"name": "Nope Nope", "expertise": "x", "bio": "y"})
    assert r.status_code == 403


# ---------- Auth ----------

def test_auth_flow(client):
    r = client.post("/auth/register", json={"email": "New@Uni.edu", "password": "password1", "full_name": "New Student"})
    assert r.status_code == 201 and r.json()["user"]["email"] == "new@uni.edu"
    assert client.post("/auth/register", json={"email": "new@uni.edu", "password": "password1", "full_name": "Dup"}).status_code == 409
    assert client.post("/auth/login", json={"email": "new@uni.edu", "password": "wrongwrong"}).status_code == 401
    assert client.get("/roadmaps/").status_code == 401
    r = client.post("/auth/register", json={"email": "prof@uni.edu", "password": "password1", "full_name": "Prof New", "role": "mentor", "expertise": "Go"})
    assert r.json()["user"]["mentor_id"] is not None


# ---------- Roadmaps / Gemini ----------

def test_roadmap_without_api_key_shows_exact_error_and_does_not_crash(client):
    h = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/roadmaps/generate", json={"goal": "Senior AI Agent Developer"}, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["source"] == "template" and "GEMINI_API_KEY is not set" in data["error_message"]
    assert len(data["milestones"]) == 4 and data["milestones"][0]["title"] != "API Connection Failed"


@pytest.mark.parametrize(
    "status_code,payload,expected",
    [
        (429, {"error": {"message": "You exceeded your current quota"}}, "Quota exceeded (HTTP 429): You exceeded your current quota"),
        (400, {"error": {"message": "API key not valid. Please pass a valid API key."}}, "API key not valid"),
    ],
)
def test_gemini_http_errors_are_passed_through(monkeypatch, status_code, payload, expected):
    class Resp:
        text = ""
        def __init__(self): self.status_code = status_code
        def json(self): return payload
    monkeypatch.setattr(ai_service.settings, "GEMINI_API_KEY", "fake")
    monkeypatch.setattr(ai_service.requests, "post", lambda *a, **k: Resp())
    result = ai_service.generate_roadmap("Data Scientist")
    assert result["source"] == "template" and expected in result["error"]


def test_gemini_success_invalid_goal_and_network_error(client, monkeypatch):
    import json

    def fake(text):
        class Resp:
            status_code = 200
            def json(self): return {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        return lambda *a, **k: Resp()

    monkeypatch.setattr(ai_service.settings, "GEMINI_API_KEY", "fake")
    h = auth(client, "student@mentorconnect.edu", "Student@123")

    good = {"valid": True, "reason": "", "milestones": [
        {"title": f"Step {i}", "description": "d", "topics": ["a", "b"], "duration_weeks": 3} for i in range(1, 5)]}
    monkeypatch.setattr(ai_service.requests, "post", fake("```json\n" + json.dumps(good) + "\n```"))
    r = client.post("/roadmaps/generate", json={"goal": "Backend Engineer"}, headers=h)
    assert r.status_code == 201 and r.json()["source"] == "gemini" and r.json()["error_message"] is None
    assert r.json()["milestones"][0]["topics"] == ["a", "b"]

    monkeypatch.setattr(ai_service.requests, "post", fake(json.dumps({"valid": False, "reason": "Mango is a fruit, not a career."})))
    r = client.post("/roadmaps/generate", json={"goal": "mango"}, headers=h)
    assert r.status_code == 422 and "fruit" in r.json()["detail"]

    def boom(*a, **k):
        raise ai_service.requests.ConnectionError("Name resolution failed")
    monkeypatch.setattr(ai_service.requests, "post", boom)
    r = client.post("/roadmaps/generate", json={"goal": "DevOps Engineer"}, headers=h)
    assert r.status_code == 201 and "Could not reach the Gemini API: Name resolution failed" in r.json()["error_message"]


def test_milestone_progress_retry_and_delete(client):
    h = auth(client, "student@mentorconnect.edu", "Student@123")
    rm = client.post("/roadmaps/generate", json={"goal": "Cloud Engineer"}, headers=h).json()
    m_id = rm["milestones"][0]["id"]
    assert client.patch(f"/milestones/{m_id}", json={"status": "completed"}, headers=h).status_code == 404
    r = client.patch(f"/roadmaps/milestones/{m_id}", json={"status": "completed"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "completed"
    assert client.get("/roadmaps/", headers=h).json()[0]["progress"] in (0, 25)
    new = client.post("/roadmaps/generate", json={"goal": "Cloud Engineer", "replace_id": rm["id"]}, headers=h).json()
    ids = [x["id"] for x in client.get("/roadmaps/", headers=h).json()]
    assert rm["id"] not in ids and new["id"] in ids
    assert client.delete(f"/roadmaps/{new['id']}", headers=h).status_code == 204


# ---------- Mentor profile, modes, slots, busy ranges, reviews ----------

def test_mentor_can_edit_profile_and_modes_follow_links(client):
    prof = auth(client, "prof@uni.edu", "password1")
    me = client.get("/mentors/me", headers=prof).json()
    # "offline" is always bookable (room can be confirmed after the fact); "teams" needs a link.
    assert me["available_modes"] == ["offline"]
    r = client.put("/mentors/me", json={"teams_link": "https://teams.example/room", "campus_location": "Room 1", "availability": "Fri 3-5 PM"}, headers=prof)
    assert r.status_code == 200 and set(r.json()["available_modes"]) == {"teams", "offline"}
    assert set(client.put("/mentors/me", json={"campus_location": ""}, headers=prof).json()["available_modes"]) == {"teams", "offline"}
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    assert client.put("/mentors/me", json={"bio": "x"}, headers=student).status_code == 403


def test_mentor_slots_and_availability_enforcement(client):
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/auth/register", json={"email": "slots.mentor@uni.edu", "password": "password1", "full_name": "Prof Slots", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mentor_id = r.json()["user"]["mentor_id"]

    r2 = client.put("/mentors/me/slots", json={"slots": [{"weekday": 0, "start_time": "10:30", "end_time": "12:30"}]}, headers=prof)
    assert r2.status_code == 200 and len(r2.json()) == 1

    d = datetime.now(timezone.utc) + timedelta(days=1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    outside = d.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
    inside = d.replace(hour=11, minute=0, second=0, microsecond=0).isoformat()

    assert client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": outside, "mode": "offline"}, headers=student).status_code == 422
    r3 = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": inside, "mode": "offline"}, headers=student)
    assert r3.status_code == 201, r3.text


def test_busy_ranges_show_active_bookings_without_revealing_who(client):
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/auth/register", json={"email": "busy.mentor@uni.edu", "password": "password1", "full_name": "Prof Busy", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mentor_id = r.json()["user"]["mentor_id"]

    assert client.get(f"/mentors/{mentor_id}/busy", headers=student).json() == []

    when = future(500)
    b = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": when, "mode": "offline"}, headers=student).json()
    ranges = client.get(f"/mentors/{mentor_id}/busy", headers=student).json()
    assert len(ranges) == 1
    blob = str(ranges).lower()
    assert "student" not in blob and "name" not in blob

    client.patch(f"/bookings/{b['id']}/status", json={"status": "cancelled", "reason": "x"}, headers=student)
    assert client.get(f"/mentors/{mentor_id}/busy", headers=student).json() == []
    assert client.get("/mentors/999999/busy", headers=student).status_code == 404
    assert client.get(f"/mentors/{mentor_id}/busy").status_code == 401


def test_reviews_endpoint_shows_ratings_without_student_identity(client):
    from sqlalchemy import select as sa_select

    from app.database import SessionLocal
    from app.models.booking import Booking
    from app.models.user import User as UserModel

    student = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/auth/register", json={"email": "reviews.mentor@uni.edu", "password": "password1", "full_name": "Prof Reviews", "role": "mentor"})
    mentor_id = r.json()["user"]["mentor_id"]
    assert client.get(f"/mentors/{mentor_id}/reviews", headers=student).json() == []

    with SessionLocal() as db:
        sid = db.scalar(sa_select(UserModel.id).where(UserModel.email == "student@mentorconnect.edu"))
        b1 = Booking(student_id=sid, mentor_id=mentor_id, mode="meet",
                     scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2),
                     duration_minutes=30, status="completed", rating=5, feedback="Really helped with my project.")
        b2 = Booking(student_id=sid, mentor_id=mentor_id, mode="meet",
                     scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=5),
                     duration_minutes=30, status="completed", rating=4, feedback=None)
        db.add_all([b1, b2]); db.commit()

    reviews = client.get(f"/mentors/{mentor_id}/reviews", headers=student).json()
    assert len(reviews) == 2
    assert reviews[0]["rating"] == 5 and "project" in reviews[0]["feedback"]
    blob = str(reviews).lower()
    assert "student" not in blob and "@" not in blob
    assert client.get("/mentors/999999/reviews", headers=student).status_code == 404


# ---------- Booking lifecycle ----------

def test_booking_lifecycle(client):
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/auth/register", json={"email": "lifecycle.mentor@uni.edu", "password": "password1", "full_name": "Prof Lifecycle", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mentor_id = r.json()["user"]["mentor_id"]
    client.put("/mentors/me", json={"meet_link": "https://meet.google.com/lifecycle-test"}, headers=prof)

    r = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(50), "mode": "meet", "topic": "API design"}, headers=student)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["meeting_link"] == "https://meet.google.com/lifecycle-test" and b["status"] == "pending" and b["scheduled_at"].endswith("Z")
    assert b["has_notes"] is False

    assert client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(50), "mode": "meet"}, headers=student).status_code == 409
    assert client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(-3), "mode": "meet"}, headers=student).status_code == 422
    assert client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(72), "mode": "meet"}, headers=prof).status_code == 403
    assert client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(96), "mode": "teams"}, headers=student).status_code == 422

    assert client.patch(f"/bookings/{b['id']}/status", json={"status": "confirmed"}, headers=student).status_code == 403
    assert client.patch(f"/bookings/{b['id']}/status", json={"status": "confirmed"}, headers=prof).json()["status"] == "confirmed"
    assert client.patch(f"/bookings/{b['id']}/status", json={"status": "completed"}, headers=prof).status_code == 409
    assert client.post(f"/bookings/{b['id']}/review", json={"rating": 5}, headers=student).status_code == 409

    assert any(x["id"] == b["id"] for x in client.get("/bookings/me", headers=student).json())
    assert any(x["id"] == b["id"] for x in client.get("/bookings/me", headers=prof).json())


def test_completed_session_rating_and_notes(client):
    """Force a past confirmed booking straight in the DB, then run completion + review + notes over the API."""
    from sqlalchemy import select as sa_select

    from app.database import SessionLocal
    from app.models.booking import Booking
    from app.models.user import User as UserModel

    student = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/auth/register", json={"email": "notes.mentor@uni.edu", "password": "password1", "full_name": "Prof Notes", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mentor = client.get("/mentors/me", headers=prof).json()

    with SessionLocal() as db:
        sid = db.scalar(sa_select(UserModel.id).where(UserModel.email == "student@mentorconnect.edu"))
        bk = Booking(student_id=sid, mentor_id=mentor["id"], scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2),
                     mode="meet", status="confirmed")
        db.add(bk); db.commit(); bid = bk.id

    assert client.patch(f"/bookings/{bid}/status", json={"status": "completed"}, headers=prof).json()["status"] == "completed"
    assert client.post(f"/bookings/{bid}/review", json={"rating": 5, "feedback": "Great"}, headers=student).json()["rating"] == 5
    assert client.post(f"/bookings/{bid}/review", json={"rating": 1}, headers=student).status_code == 409
    updated = client.get(f"/mentors/{mentor['id']}").json()
    assert updated["rating_count"] == mentor["rating_count"] + 1
    assert updated["sessions_completed"] == mentor["sessions_completed"] + 1

    assert client.post(f"/bookings/{bid}/notes", json={"feedback": "Good session on APIs."}, headers=student).status_code == 403
    r = client.post(f"/bookings/{bid}/notes", json={"feedback": "Good session on API design, needs to practice pagination."}, headers=prof)
    assert r.status_code == 201, r.text
    note = r.json()
    assert note["source"] == "template"
    assert client.post(f"/bookings/{bid}/notes", json={"feedback": "Again"}, headers=prof).status_code == 409

    booking_now = next(x for x in client.get("/bookings/me", headers=prof).json() if x["id"] == bid)
    assert booking_now["has_notes"] is True

    got = client.get(f"/bookings/{bid}/notes", headers=student).json()
    assert got["id"] == note["id"]
    stranger = auth(client, "prof@uni.edu", "password1")
    assert client.get(f"/bookings/{bid}/notes", headers=stranger).status_code == 403


def test_reschedule_and_cancel(client):
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/auth/register", json={"email": "reschedule.mentor@uni.edu", "password": "password1", "full_name": "Prof Reschedule", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mentor_id = r.json()["user"]["mentor_id"]
    client.put("/mentors/me", json={"meet_link": "https://meet.google.com/reschedule-test"}, headers=prof)

    b = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(60), "mode": "meet"}, headers=student).json()
    r2 = client.patch(f"/bookings/{b['id']}/reschedule", json={"scheduled_at": future(90), "reason": "clash"}, headers=student)
    assert r2.status_code == 200 and r2.json()["reschedule_count"] == 1

    r3 = client.patch(f"/bookings/{b['id']}/status", json={"status": "cancelled", "reason": "no longer needed"}, headers=student)
    assert r3.status_code == 200 and r3.json()["cancelled_by"] == "student"
    b2 = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(120), "mode": "meet"}, headers=student).json()
    assert client.patch(f"/bookings/{b2['id']}/status", json={"status": "cancelled"}, headers=student).status_code == 422


# ---------- Room editing (on-campus sessions) ----------

def test_mentor_can_set_and_change_room_per_session(client):
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    r = client.post("/auth/register", json={"email": "room.mentor@uni.edu", "password": "password1", "full_name": "Prof Room Test", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mentor_id = r.json()["user"]["mentor_id"]

    mentor = next(m for m in client.get("/mentors/").json() if m["id"] == mentor_id)
    assert "offline" in mentor["available_modes"]
    r = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(3000), "mode": "offline"}, headers=student)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["location"] is None

    r = client.patch(f"/bookings/{b['id']}/location", json={"location": "Block D, Room 101"}, headers=prof)
    assert r.status_code == 200 and r.json()["location"] == "Block D, Room 101"

    assert client.patch(f"/bookings/{b['id']}/location", json={"location": "Nope"}, headers=student).status_code == 403
    other = auth(client, "prof@uni.edu", "password1")
    assert client.patch(f"/bookings/{b['id']}/location", json={"location": "Nope"}, headers=other).status_code == 404

    client.put("/mentors/me", json={"meet_link": "https://meet.google.com/room-test"}, headers=prof)
    r = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(3050), "mode": "meet"}, headers=student)
    assert r.status_code == 201, r.text
    online = r.json()
    assert client.patch(f"/bookings/{online['id']}/location", json={"location": "X"}, headers=prof).status_code == 422


# ---------- Student academic details ----------

def test_mentor_sees_student_academic_details_on_their_booking(client):
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    client.put("/students/me", json={
        "institute_type": "college", "institute_name": "Vidyalankar Institute of Technology (VIT)",
        "roll_number": "24101B0065", "program_level": "UG", "year_of_study": "Third", "branch": "Information Technology",
    }, headers=student)

    r = client.post("/auth/register", json={"email": "academic.mentor@uni.edu", "password": "password1", "full_name": "Prof Academic", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    mentor_id = r.json()["user"]["mentor_id"]
    client.put("/mentors/me", json={"meet_link": "https://meet.google.com/academic-test"}, headers=prof)

    b = client.post("/bookings/", json={"mentor_id": mentor_id, "scheduled_at": future(3200), "mode": "meet"}, headers=student).json()
    mine = next(x for x in client.get("/bookings/me", headers=prof).json() if x["id"] == b["id"])
    assert mine["student_academic"]["roll_number"] == "24101B0065"
    assert mine["student_academic"]["branch"] == "Information Technology"


# ---------- "Remembers this student" (redesigned: same mentor only, never cross-mentor) ----------

def test_memory_is_scoped_to_the_same_mentor_only(client):
    from sqlalchemy import select as sa_select

    from app.database import SessionLocal
    from app.models.booking import Booking
    from app.models.user import User as UserModel

    r1 = client.post("/auth/register", json={"email": "memory.student@uni.edu", "password": "password1", "full_name": "Memory Student"})
    student = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    sid = r1.json()["user"]["id"]

    r2 = client.post("/auth/register", json={"email": "memory.mentor1@uni.edu", "password": "password1", "full_name": "Prof Memory One", "role": "mentor"})
    prof1 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    mentor1_id = r2.json()["user"]["mentor_id"]

    r3 = client.post("/auth/register", json={"email": "memory.mentor2@uni.edu", "password": "password1", "full_name": "Prof Memory Two", "role": "mentor"})
    prof2 = {"Authorization": f"Bearer {r3.json()['access_token']}"}
    mentor2_id = r3.json()["user"]["mentor_id"]

    assert client.get(f"/mentors/students/{sid}/memory", headers=prof1).status_code == 403

    with SessionLocal() as db:
        bk = Booking(student_id=sid, mentor_id=mentor1_id, mode="meet",
                     scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2), status="confirmed")
        db.add(bk); db.commit(); bid = bk.id
    client.patch(f"/bookings/{bid}/status", json={"status": "completed"}, headers=prof1)
    client.post(f"/bookings/{bid}/notes", json={"feedback": "Worked through recursion and base cases together."}, headers=prof1)

    assert client.get(f"/mentors/students/{sid}/memory", headers=prof1).status_code == 403

    r_b2 = client.post("/bookings/", json={"mentor_id": mentor1_id, "scheduled_at": future(200), "mode": "offline"}, headers=student)
    assert r_b2.status_code == 201, r_b2.text
    b2 = r_b2.json()
    client.patch(f"/bookings/{b2['id']}/status", json={"status": "confirmed"}, headers=prof1)
    mem1 = client.get(f"/mentors/students/{sid}/memory", headers=prof1).json()
    assert mem1["student_name"] == "Memory Student"
    assert len(mem1["sessions"]) == 1
    assert "recursion" in str(mem1["sessions"][0]).lower()

    assert client.get(f"/mentors/students/{sid}/memory", headers=prof2).status_code == 403
    r_b3 = client.post("/bookings/", json={"mentor_id": mentor2_id, "scheduled_at": future(250), "mode": "offline"}, headers=student)
    assert r_b3.status_code == 201, r_b3.text
    b3 = r_b3.json()
    client.patch(f"/bookings/{b3['id']}/status", json={"status": "confirmed"}, headers=prof2)
    mem2 = client.get(f"/mentors/students/{sid}/memory", headers=prof2).json()
    assert mem2["sessions"] == []


def test_action_items_dashboard_was_removed(client):
    student = auth(client, "student@mentorconnect.edu", "Student@123")
    assert client.get("/students/me/action-items", headers=student).status_code == 404


# ---------- Admin verification ----------

def test_verification_queue_and_review(client, tmp_path):
    r = client.post("/auth/register", json={"email": "verify.mentor@uni.edu", "password": "password1", "full_name": "Prof Verify", "role": "mentor"})
    prof = {"Authorization": f"Bearer {r.json()['access_token']}"}
    admin = auth(client, "admin@mentorconnect.edu", "Admin@123")

    doc = tmp_path / "id.pdf"
    doc.write_bytes(b"%PDF-1.4 fake")
    with open(doc, "rb") as f:
        r2 = client.post(
            "/mentors/me/verification",
            data={"path": "academic"},
            files={"document": ("id.pdf", f, "application/pdf")},
            headers=prof,
        )
    assert r2.status_code == 201 and r2.json()["status"] == "pending"

    pending = client.get("/admin/verifications", params={"status_filter": "pending"}, headers=admin).json()
    assert any(item["name"] == "Prof Verify" for item in pending)

    mentor_id = r.json()["user"]["mentor_id"]
    r3 = client.post(f"/admin/verifications/{mentor_id}/approve", headers=admin)
    assert r3.status_code == 200 and r3.json()["status"] == "verified" and r3.json()["platform_verified"] is True

    student = auth(client, "student@mentorconnect.edu", "Student@123")
    assert client.post(f"/admin/verifications/{mentor_id}/approve", headers=student).status_code == 403
