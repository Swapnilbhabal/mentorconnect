# MentorConnect

A platform where students turn a career goal into an AI-generated roadmap, then book sessions with verified professors.

- **Backend:** FastAPI, SQLAlchemy (SQLite), Pydantic, JWT login
- **AI:** Google Gemini (called through `requests`, so no SDK version issues)
- **Frontend:** React + Vite

## What's included

| Feature | Details |
|---|---|
| Role-based login | Students and professors register and sign in; each gets their own dashboard |
| AI career roadmaps | Gemini builds 4 milestones for any goal, saved per student, with progress tracking (Pending / In progress / Completed) |
| Graceful AI failures | If Gemini fails (no key, quota exceeded, network), the app **doesn't crash**: it shows the **exact error message** on screen plus a clearly labelled template roadmap and a *Retry* button |
| Goal validation | Nonsense goals such as "mango" are rejected by Gemini with a reason instead of producing a fake roadmap |
| Mentor network | Search by name/expertise, filter by skill, meeting type and minimum score, sort by score / experience / name |
| Effectiveness score | 70% average student rating + 30% session completion rate (see `backend/app/services/scoring.py`) |
| Booking with Meet / Teams routing | Students pick Google Meet, Teams or on-campus. The booking stores that professor's own link or location. Clash detection for both sides |
| Session lifecycle | Pending, Confirmed, Completed, Cancelled. Students rate completed sessions, which updates the professor's score |
| Seeder | `seed_teachers.py` registers 8 professors with logins and `ui-avatars.com` profile pictures |

## Quick start

You need **Python 3.10+** and **Node 18+**.

### 1. Backend (terminal 1)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

copy .env.example .env         # Windows   (macOS/Linux: cp .env.example .env)
# open .env and paste your GEMINI_API_KEY (see below)

uvicorn main:app --reload
```

The API runs at http://127.0.0.1:8000 (interactive docs at `/docs`). On first start, the empty database is filled with demo professors and one demo student automatically. To seed manually, or start over, run `python seed_teachers.py` or `python seed_teachers.py --reset`.

### 2. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Demo logins

| Role | Email | Password |
|---|---|---|
| Student | `student@mentorconnect.edu` | `Student@123` |
| Professor | `sarah.connor@mentorconnect.edu` (or any other from the seeder output) | `Mentor@123` |

## Getting a Gemini API key

1. Go to https://aistudio.google.com/app/apikey and click **Create API key**.
2. If the dialog shows **"No Cloud Projects Available"**, choose **Create project**, then create the key inside it. The free tier is enough for this app.
3. Paste it into `backend/.env` as `GEMINI_API_KEY=...` and **restart uvicorn**.
4. The hub shows a green **All systems normal** when the key is loaded, and amber **Gemini key missing** when it isn't.

## Troubleshooting

| You see | Cause and fix |
|---|---|
| Amber banner: `GEMINI_API_KEY is not set` | Key missing in `backend/.env`, or the server wasn't restarted after adding it |
| `Quota exceeded (HTTP 429): …` | Free-tier limit reached. Wait a minute, or use a different model via `GEMINI_MODEL` |
| `Gemini returned HTTP 404: … model … not found` | Google retired the model name. Set `GEMINI_MODEL` in `.env` to a current one (see https://ai.google.dev/gemini-api/docs/models) |
| `API key not valid` | Wrong or revoked key. Create a new one |
| `Can't reach the MentorConnect server` | Backend isn't running, or `VITE_API_URL` in `frontend/.env` points somewhere else |
| `422 … user_id Field required` at `/docs` | Fixed: `POST /mentors/` no longer needs a `user_id` |
| Profile pictures show initials | Offline or `ui-avatars.com` is blocked. Initials are the built-in fallback |

## Project layout

```
mentor_connect/
├── backend/
│   ├── main.py                 # app entry point (uvicorn main:app)
│   ├── seed_teachers.py        # demo professors + student
│   ├── requirements.txt
│   ├── .env.example
│   ├── tests/test_api.py       # 12 end-to-end tests (no API key or internet needed)
│   └── app/
│       ├── config.py, database.py, security.py, seed.py
│       ├── models/             # user, mentor, roadmap (+milestone), booking
│       ├── schemas/            # Pydantic request/response models
│       ├── routers/            # auth, mentors, roadmaps, bookings
│       └── services/           # ai_service (Gemini), scoring, serializers, avatars
└── frontend/
    ├── index.html, package.json, vite.config.js
    └── src/
        ├── main.jsx, App.jsx, api.js, index.css
        └── components/         # Landing, AuthPage, StudentHub, MentorHub, RoadmapPanel,
                                # MentorNetwork, BookingDialog, SessionList, Navbar, ui
```

## API overview

| Method | Path | Who | Purpose |
|---|---|---|---|
| POST | `/auth/register`, `/auth/login` | anyone | Create an account / get a token |
| GET | `/auth/me` | logged in | Current user |
| GET | `/mentors/` | anyone | List with `q`, `expertise`, `mode`, `min_score`, `sort` |
| GET | `/mentors/skills` | anyone | All skills, for the filter dropdown |
| POST | `/mentors/` | anyone* | Create a mentor profile (`user_id` optional) |
| GET / PUT | `/mentors/me` | mentor | View / edit own profile and meeting links |
| POST | `/roadmaps/generate` | logged in | Generate a roadmap with Gemini |
| GET | `/roadmaps/` | logged in | My roadmaps |
| PATCH | `/roadmaps/milestones/{id}` | owner | Update milestone status |
| DELETE | `/roadmaps/{id}` | owner | Delete a roadmap |
| POST | `/bookings/` | student | Request a session |
| GET | `/bookings/me` | logged in | My sessions (student) or requests (mentor) |
| PATCH | `/bookings/{id}/status` | student / mentor | Confirm, complete, cancel |
| POST | `/bookings/{id}/review` | student | Rate a completed session |

\* Open by default so you can test from `/docs`. Set `ALLOW_OPEN_MENTOR_CREATION=false` in `.env` before deploying, otherwise anyone can add a mentor.

## Before you deploy

- Set a long random `SECRET_KEY` in `.env`.
- Set `ALLOW_OPEN_MENTOR_CREATION=false` and `CORS_ORIGINS` to your real frontend URL.
- The seeded professors' **Meet and Teams links are placeholders**. Each professor should paste their own in *My profile*. The app routes students to whatever link the professor saved. It does not create new Meet/Teams meetings (that needs the Google Calendar / Microsoft Graph APIs).
- The "Reach us" e-mail on the landing page (`hello@mentorconnect.example`) is a placeholder.
- Run the tests after any change: `pip install -r requirements-dev.txt` then `python -m pytest -q` in `backend/`.
