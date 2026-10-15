"""Gemini roadmap generation.

Talks to the Gemini REST API with `requests`, so it does not depend on which Google SDK version is installed.
This function NEVER raises: every failure is returned as an exact, human readable `error` string so the UI can
show it, and the platform keeps working with a clearly-labelled template roadmap.
"""
from __future__ import annotations

import json
import re
import time

import requests

from ..config import settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# HTTP statuses worth retrying: 503 = Google's servers are overloaded, 429 = rate limited,
# 500/502/504 = generic upstream trouble. These are almost always transient and often clear
# within a few seconds, so a short retry loop turns a flaky moment into a normal success
# instead of a visible failure (important during a live demo).
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 1.5

PROMPT = """You are a career mentor for university students. Build a practical 4-milestone learning roadmap for the goal below.

Goal: "{goal}"

Rules:
- First decide whether the goal is a real career role, skill or field of study a student could work toward.
  If it is not (for example a fruit, gibberish, or something unsafe), set "valid" to false and explain briefly in "reason".
- Otherwise set "valid" to true and return exactly 4 sequential milestones tailored to this goal:
  1. foundations, 2. core tools/frameworks/data structures for this specific field,
  3. a capstone, production-style project for a portfolio, 4. interview and placement readiness.
- Each milestone: a short "title" (max 8 words), a one or two sentence "description",
  3 to 5 concrete "topics" (specific technologies, concepts or deliverables), and "duration_weeks" (integer 1-12).
- Be specific to the goal. Do not use generic filler.

Return ONLY JSON in this shape:
{{"valid": true, "reason": "", "milestones": [{{"title": "", "description": "", "topics": ["", ""], "duration_weeks": 4}}]}}"""


def _template(goal: str) -> list[dict]:
    """Shown only when the AI call fails, so the student still has something to work with."""
    return [
        {
            "title": "Foundational Skills",
            "description": f"Master the core competencies required for {goal}.",
            "topics": ["Core concepts", "Fundamentals of the field", "Version control with Git"],
            "duration_weeks": 4,
        },
        {
            "title": "Data Structures & Core Tooling",
            "description": "Build proficiency in essential frameworks and libraries.",
            "topics": ["Data structures & algorithms", "Primary frameworks", "Testing and debugging"],
            "duration_weeks": 6,
        },
        {
            "title": "Capstone Project & Portfolio",
            "description": f"Develop a production-grade MVP demonstrating expertise in {goal}.",
            "topics": ["Project scoping", "Deployment", "Portfolio write-up"],
            "duration_weeks": 6,
        },
        {
            "title": "Mock Interviews & Readiness",
            "description": "Undergo AI and peer mock interviews to achieve placement readiness.",
            "topics": ["Technical interviews", "System design basics", "Resume review"],
            "duration_weeks": 2,
        },
    ]


def _fallback(goal: str, error: str) -> dict:
    return {"source": "template", "error": error, "invalid_reason": None, "milestones": _template(goal)}


def _extract_google_error(resp: requests.Response) -> str:
    try:
        return resp.json()["error"]["message"]
    except Exception:  # noqa: BLE001 - any parsing problem falls back to the raw text
        return (resp.text or "").strip()[:500] or "No error details were returned."


def _clean_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    return json.loads(text)


def _normalise_milestones(raw: list) -> list[dict]:
    milestones = []
    for item in raw[:6]:
        if not isinstance(item, dict) or not str(item.get("title", "")).strip():
            continue
        topics = [str(t).strip() for t in (item.get("topics") or []) if str(t).strip()][:6]
        weeks = item.get("duration_weeks")
        milestones.append(
            {
                "title": str(item["title"]).strip()[:200],
                "description": str(item.get("description", "")).strip(),
                "topics": topics,
                "duration_weeks": int(weeks) if isinstance(weeks, (int, float)) and 0 < weeks < 53 else None,
            }
        )
    return milestones


def generate_roadmap(goal: str) -> dict:
    """Returns {"source", "error", "invalid_reason", "milestones"}."""
    if not settings.GEMINI_API_KEY:
        return _fallback(
            goal,
            "GEMINI_API_KEY is not set. Add your key to backend/.env and restart the server.",
        )

    url = GEMINI_URL.format(model=settings.GEMINI_MODEL)
    body = {
        "contents": [{"role": "user", "parts": [{"text": PROMPT.format(goal=goal.replace('"', "'"))}]}],
        "generationConfig": {"temperature": 0.6, "responseMimeType": "application/json"},
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
        time.sleep(_RETRY_DELAY_SECONDS)  # brief pause before retrying a likely-transient failure

    if network_error is not None:
        return _fallback(goal, network_error + " Try again.")

    if resp.status_code != 200:
        message = _extract_google_error(resp)
        if resp.status_code == 429:
            message = f"Quota exceeded (HTTP 429): {message}"
        elif resp.status_code == 503:
            message = f"Gemini is temporarily overloaded (HTTP 503) after {_MAX_ATTEMPTS} attempts: {message}"
        else:
            message = f"Gemini returned HTTP {resp.status_code}: {message}"
        return _fallback(goal, message)

    try:
        data = resp.json()
        block = (data.get("promptFeedback") or {}).get("blockReason")
        if block:
            return _fallback(goal, f"Gemini blocked this request ({block}). Try rephrasing the goal.")
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = _clean_json(text)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return _fallback(goal, f"Gemini returned a response the app could not read ({type(exc).__name__}: {exc}).")

    if parsed.get("valid") is False:
        reason = str(parsed.get("reason") or "That doesn't look like a career goal.").strip()
        return {"source": "gemini", "error": None, "invalid_reason": reason, "milestones": []}

    milestones = _normalise_milestones(parsed.get("milestones") or [])
    if len(milestones) < 2:
        return _fallback(goal, "Gemini did not return enough milestones. Try again.")

    return {"source": "gemini", "error": None, "invalid_reason": None, "milestones": milestones}