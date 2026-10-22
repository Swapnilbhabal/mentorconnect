from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

from sqlalchemy.pool import NullPool

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs = {"connect_args": _connect_args, "pool_pre_ping": True}
if not _is_sqlite:
    _engine_kwargs["poolclass"] = NullPool  # serverless: don't hold a pool open between invocations
engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite does not store timezones)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
