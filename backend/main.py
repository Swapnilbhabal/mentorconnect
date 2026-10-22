"""MentorConnect API.   Run from the backend folder:  uvicorn main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401 - registers the tables
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.migrate import auto_migrate
from app.routers import admin, auth, bookings, mentors, notifications, roadmaps, session_notes, students
from app.seed import seed_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates any brand-new table
    changes = auto_migrate(engine)  # adds any new columns to tables that already existed
    if changes:
        print(f"[migrate] added {len(changes)} column(s): {', '.join(changes)}")
    if settings.AUTO_SEED:
        # seed_database is idempotent (matches by email), so it's safe to call on every
        # startup -- this also means anyone upgrading from an older database automatically
        # gets new seeded accounts (like the demo admin) without needing to reset anything.
        with SessionLocal() as db:
            seed_database(db)
    yield


app = FastAPI(title="MentorConnect API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(mentors.router)
app.include_router(roadmaps.router)
app.include_router(bookings.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(students.router)
app.include_router(session_notes.router)


@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "ai_configured": bool(settings.GEMINI_API_KEY),
        "model": settings.GEMINI_MODEL,
        "zoom_configured": settings.ZOOM_ENABLED,
    }


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    """Last line of defence: the API answers with JSON instead of dropping the connection."""
    return JSONResponse(status_code=500, content={"detail": f"Unexpected server error: {type(exc).__name__}: {exc}"})