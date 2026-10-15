"""Zoom Server-to-Server OAuth: creates a real, unique meeting per booking.

Uses one platform-owned Zoom account (yours), so mentors never need to connect their own
Zoom/Google/Microsoft account. Unlike a shared "meet.google.com/new" link, each call here
returns a distinct join_url tied to one specific meeting -- both the mentor and student get
that exact same link and land in the same room.

Like the Gemini integration, this NEVER raises: every failure comes back as an error string
so the caller can decide what to do (fall back to a static link, or fail the booking clearly).
"""
from __future__ import annotations

import base64
import time

import requests

from ..config import settings

TOKEN_URL = "https://zoom.us/oauth/token"
MEETINGS_URL = "https://api.zoom.us/v2/users/me/meetings"

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 1.5

_token_cache: dict = {"token": None, "expires_at": 0}


def _get_access_token() -> tuple[str | None, str | None]:
    """Returns (token, error). Cached until ~60s before expiry to avoid a token call on every booking."""
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"], None

    creds = f"{settings.ZOOM_CLIENT_ID}:{settings.ZOOM_CLIENT_SECRET}".encode()
    headers = {"Authorization": f"Basic {base64.b64encode(creds).decode()}"}
    params = {"grant_type": "account_credentials", "account_id": settings.ZOOM_ACCOUNT_ID}

    try:
        resp = requests.post(TOKEN_URL, headers=headers, params=params, timeout=15)
    except requests.RequestException as exc:
        return None, f"Could not reach Zoom to authenticate: {exc}"

    if resp.status_code != 200:
        try:
            msg = resp.json().get("reason") or resp.text
        except ValueError:
            msg = resp.text
        return None, f"Zoom authentication failed (HTTP {resp.status_code}): {msg}"

    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["token"], None


def create_meeting(topic: str, start_time: str, duration_minutes: int) -> dict:
    """start_time: ISO 8601 UTC string, e.g. '2026-09-25T14:00:00Z'.
    Returns {"join_url": str | None, "error": str | None}. Never raises."""
    if not settings.ZOOM_ENABLED:
        return {"join_url": None, "error": "Zoom is not configured (ZOOM_ACCOUNT_ID/CLIENT_ID/CLIENT_SECRET missing)."}

    token, error = _get_access_token()
    if error:
        return {"join_url": None, "error": error}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "topic": topic[:200],
        "type": 2,  # scheduled meeting
        "start_time": start_time,
        "duration": duration_minutes,
        "timezone": "UTC",
        "settings": {"join_before_host": True, "waiting_room": False, "approval_type": 2},
    }

    resp = None
    network_error = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        network_error = None
        try:
            resp = requests.post(MEETINGS_URL, json=body, headers=headers, timeout=20)
        except requests.RequestException as exc:
            network_error = f"Could not reach Zoom: {exc}"

        transient = network_error is not None or (resp is not None and resp.status_code in _RETRYABLE_STATUSES)
        if not transient or attempt == _MAX_ATTEMPTS:
            break
        time.sleep(_RETRY_DELAY_SECONDS)

    if network_error:
        return {"join_url": None, "error": network_error}

    if resp.status_code not in (200, 201):
        try:
            msg = resp.json().get("message") or resp.text
        except ValueError:
            msg = resp.text
        return {"join_url": None, "error": f"Zoom returned HTTP {resp.status_code}: {msg}"}

    return {"join_url": resp.json().get("join_url"), "error": None}