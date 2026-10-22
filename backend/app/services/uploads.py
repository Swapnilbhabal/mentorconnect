"""Safe on-disk storage for mentor verification documents (SRS REQ-2-1).

NOTE: files are stored on the local filesystem under settings.UPLOAD_DIR. On most free
hosting tiers this folder does NOT survive a redeploy/restart -- fine for local testing and
a demo, but swap this for real object storage (S3, Cloudflare R2, etc.) before relying on it
in production.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from ..config import settings

_EXT_BY_TYPE = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def _safe_stem(name: str) -> str:
    stem = Path(name).stem[:60]
    return re.sub(r"[^A-Za-z0-9_-]+", "-", stem) or "document"


async def save_verification_document(mentor_id: int, file: UploadFile) -> tuple[str, bytes, str]:
    """Validates type/size and returns (display_name, file_bytes, content_type).
    Raises HTTPException(422) with a clear message on anything invalid -- never crashes."""
    content_type = (file.content_type or "").lower()
    if content_type not in settings.ALLOWED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{content_type or 'unknown'}'. Upload a PDF, JPG or PNG.",
        )

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(status_code=422, detail=f"File is too large. Maximum size is {settings.MAX_UPLOAD_MB}MB.")
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    return file.filename or f"mentor{mentor_id}-document", data, content_type