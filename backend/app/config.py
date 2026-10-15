"""Central configuration, read from environment variables / backend/.env"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'mentorconnect_v3.db'}")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-secret-change-me-before-deploying-1234567890")
    TOKEN_EXPIRE_HOURS: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "72"))

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))

    ZOOM_ACCOUNT_ID: str = os.getenv("ZOOM_ACCOUNT_ID", "").strip()
    ZOOM_CLIENT_ID: str = os.getenv("ZOOM_CLIENT_ID", "").strip()
    ZOOM_CLIENT_SECRET: str = os.getenv("ZOOM_CLIENT_SECRET", "").strip()

    @property
    def ZOOM_ENABLED(self) -> bool:
        return bool(self.ZOOM_ACCOUNT_ID and self.ZOOM_CLIENT_ID and self.ZOOM_CLIENT_SECRET)

    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if o.strip()
    ]
    # POST /mentors/ without logging in (handy for /docs testing). Set to false for production.
    ALLOW_OPEN_MENTOR_CREATION: bool = os.getenv("ALLOW_OPEN_MENTOR_CREATION", "true").lower() in ("1", "true", "yes")
    AUTO_SEED: bool = os.getenv("AUTO_SEED", "true").lower() in ("1", "true", "yes")

    # Where mentor verification documents (ID cards, offer letters, etc.) are stored.
    # NOTE: on most free hosting tiers this folder is wiped on every redeploy/restart --
    # for anything beyond local testing, swap this for real object storage (S3, etc.).
    UPLOAD_DIR: Path = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "5"))
    ALLOWED_UPLOAD_TYPES: set[str] = {"application/pdf", "image/jpeg", "image/png"}


settings = Settings()