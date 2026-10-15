"""Turns a mentor's quick raw post-session notes into structured feedback (SRS 4.5).

REQ-6-2: Gemini formats raw feedback into distinct Strengths / Weaknesses / Action Items.
REQ-6-3: each action item gets an automatic deadline.

Mirrors ai_service.py's retry-and-fallback pattern exactly (same reasoning: a brief Gemini
outage shouldn't lose a mentor's notes). NEVER raises -- on any failure, the mentor's raw
feedback is preserved as a single fallback action item rather than being lost.
"""
from __future__ import annotations

import json
import re
import time

import requests

from ..config import settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 1.5

PROMPT = """You are helping a mentor turn quick raw notes into structured feedback for a student after a one-to-one mentoring session.

Session topic: "{topic}"
Mentor's raw notes: "{feedback}"

Rules:
- If the notes are too short or vague to extract anything meaningful (e.g. "good session", "nothing much", empty), set "valid" to false with a brief "reason".
- Otherwise extract 2-4 specific "strengths", 1-3 specific "weaknesses", and 1-4 concrete "action_items".
- Each action item needs "item" (a specific, actionable task the student should do) and "days" (integer 1-30: a reasonable number of days from today for its deadline given how substantial the task is).
- Base everything only on what the mentor actually wrote. Do not invent details that aren't implied by the notes.

Return ONLY JSON in this shape:
{{"valid": true, "reason": "", "strengths": ["...", "..."], "weaknesses": ["...", "..."], "action_items": [{{"item": "...", "days": 7}}]}}"""


def _fallback(feedback: str, error: str) -> dict:
    """Shown only when the AI call fails -- keeps the mentor's raw notes visible as a single
    action item instead of losing them."""
    return {
        "source": "template",
        "error": error,
        "invalid_reason": None,
        "strengths": [],
        "weaknesses": [],
        "action_items": [{"item": f"Review mentor's notes: {feedback[:240]}", "days": 7}],
    }


def _extract_google_error(resp: requests.Response) -> str:
    try:
        return resp.json()["error"]["message"]
    except Exception:  # noqa: BLE001 - any parsing problem falls back to the raw text
        return (resp.text or "").strip()[:500] or "No error details were returned."


def _clean_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    return json.loads(text)


def _normalise_action_items(raw: list) -> list[dict]:
    items = []
    for item in raw[:6]:
        if not isinstance(item, dict) or not str(item.get("item", "")).strip():
            continue
        days = item.get("days")
        days = int(days) if isinstance(days, (int, float)) and 1 <= days <= 60 else 7
        items.append({"item": str(item["item"]).strip()[:300], "days": days})
    return items


def generate_session_notes(feedback: str, topic: str) -> dict:
    """Returns {"source", "error", "invalid_reason", "strengths", "weaknesses", "action_items"}."""
    if not settings.GEMINI_API_KEY:
        return _fallback(feedback, "GEMINI_API_KEY is not set. Add your key to backend/.env and restart the server.")

    url = GEMINI_URL.format(model=settings.GEMINI_MODEL)
    body = {
        "contents": [{"role": "user", "parts": [{"text": PROMPT.format(
            topic=topic.replace('"', "'"), feedback=feedback.replace('"', "'"),
        )}]}],
        "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"},
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY}

    resp = None
    network_error = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        network_error = None
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=settings.GEMINI_TIMEOUT_SECONDS)
        except requests.Timeout:
            network_error = f"The Gemini request timed out after {settings.GEMINI_TIMEOUT_SECONDS} seconds."
        except requests.RequestException as exc:
            network_error = f"Could not reach the Gemini API: {exc}"

        transient = network_error is not None or (resp is not None and resp.status_code in _RETRYABLE_STATUSES)
        if not transient or attempt == _MAX_ATTEMPTS:
            break
        time.sleep(_RETRY_DELAY_SECONDS)

    if network_error is not None:
        return _fallback(feedback, network_error + " Try again.")

    if resp.status_code != 200:
        message = _extract_google_error(resp)
        if resp.status_code == 429:
            message = f"Quota exceeded (HTTP 429): {message}"
        elif resp.status_code == 503:
            message = f"Gemini is temporarily overloaded (HTTP 503) after {_MAX_ATTEMPTS} attempts: {message}"
        else:
            message = f"Gemini returned HTTP {resp.status_code}: {message}"
        return _fallback(feedback, message)

    try:
        data = resp.json()
        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:
            return _fallback(feedback, f"Gemini blocked this request ({block}).")
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _clean_json(text)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return _fallback(feedback, f"Gemini returned a response the app could not read ({type(exc).__name__}: {exc}).")

    if parsed.get("valid") is False:
        reason = str(parsed.get("reason") or "These notes are too brief to structure into feedback.").strip()
        return {"source": "gemini", "error": None, "invalid_reason": reason, "strengths": [], "weaknesses": [], "action_items": []}

    action_items = _normalise_action_items(parsed.get("action_items") or [])
    strengths = [str(s).strip()[:200] for s in (parsed.get("strengths") or []) if str(s).strip()][:6]
    weaknesses = [str(s).strip()[:200] for s in (parsed.get("weaknesses") or []) if str(s).strip()][:6]

    if not strengths and not weaknesses and not action_items:
        return _fallback(feedback, "Gemini did not return any usable feedback. Try again.")

    return {"source": "gemini", "error": None, "invalid_reason": None, "strengths": strengths, "weaknesses": weaknesses, "action_items": action_items}