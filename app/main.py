from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
DATA_DIR = Path(os.getenv("CIVICEYE_DATA_DIR", str(ROOT))).expanduser()
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "civiceye.db"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="CivicEye", description="A community civic issue reporting demo")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

CATEGORIES = {
    "Roads & potholes",
    "Streetlights & electricity",
    "Waste & cleanliness",
    "Water & leaks",
    "Drainage & flooding",
    "Footpaths & accessibility",
    "Traffic signs & signals",
    "Parks & trees",
    "Other",
}
STATUSES = {"Submitted", "In progress", "Resolved"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            photo_path TEXT,
            status TEXT NOT NULL DEFAULT 'Submitted',
            priority TEXT NOT NULL DEFAULT 'Normal',
            ai_summary TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )""")


def fallback_triage(category: str, description: str) -> dict[str, str]:
    """Local, transparent triage. It is a hint for the demo, not a safety decision."""
    text = description.lower()
    urgent_terms = ("danger", "injury", "accident", "exposed wire", "open manhole", "flood")
    priority = "High" if any(term in text for term in urgent_terms) else "Normal"
    first_sentence = re.split(r"(?<=[.!?])\s+", description.strip())[0][:180]
    return {"priority": priority, "summary": f"{category} issue reported: {first_sentence}"}


def ai_triage(category: str, description: str) -> dict[str, str]:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return fallback_triage(category, description)

    endpoint = os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("AI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Triage a citizen-submitted civic issue. Return JSON with priority (High or Normal) and summary (one short sentence). Only use High for clear immediate public safety hazards. This is advisory; do not claim verification or dispatch."},
            {"role": "user", "content": f"Category: {category}\nDescription: {description[:1500]}"},
        ],
    }
    req = Request(endpoint, data=json.dumps(payload).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"
    }, method="POST")
    try:
        with urlopen(req, timeout=8) as response:
            result = json.loads(response.read())
        content = result["choices"][0]["message"]["content"]
        triage = json.loads(content)
        priority = "High" if triage.get("priority") == "High" else "Normal"
        summary = str(triage.get("summary", ""))[:240].strip()
        if not summary:
            raise ValueError("AI response omitted summary")
        return {"priority": priority, "summary": summary}
    except (URLError, TimeoutError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        # Keep reporting available if the AI service is offline or misconfigured.
        return fallback_triage(category, description)


def report_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["photo_url"] = f"/uploads/{result['photo_path']}" if result["photo_path"] else None
    result.pop("photo_path", None)
    return result


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/reports")
def list_reports():
    with connect() as db:
        rows = db.execute("SELECT * FROM reports ORDER BY created_at DESC, id DESC").fetchall()
        counts = db.execute("SELECT status, COUNT(*) AS n FROM reports GROUP BY status").fetchall()
    return {"reports": [report_dict(row) for row in rows], "counts": {r["status"]: r["n"] for r in counts}}


@app.post("/api/reports", status_code=201)
async def create_report(
    title: Annotated[str, Form()],
    category: Annotated[str, Form()],
    description: Annotated[str, Form()],
    location: Annotated[str, Form()],
    photo: Annotated[UploadFile | None, File()] = None,
):
    title, description, location = title.strip(), description.strip(), location.strip()
    if not title or len(title) > 100:
        raise HTTPException(422, "Title must be between 1 and 100 characters.")
    if category not in CATEGORIES:
        raise HTTPException(422, "Choose a valid issue category.")
    if not description or len(description) > 2000:
        raise HTTPException(422, "Description must be between 1 and 2,000 characters.")
    if not location or len(location) > 160:
        raise HTTPException(422, "Location must be between 1 and 160 characters.")

    saved_name = None
    if photo and photo.filename:
        extension = ALLOWED_IMAGE_TYPES.get(photo.content_type or "")
        if not extension:
            raise HTTPException(415, "Upload a JPG, PNG, or WebP image.")
        content = await photo.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise HTTPException(413, "Image must be 8 MB or smaller.")
        saved_name = f"{uuid.uuid4().hex}{extension}"
        (UPLOAD_DIR / saved_name).write_bytes(content)

    triage = ai_triage(category, description)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO reports (title, category, description, location, photo_path, priority, ai_summary, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, category, description, location, saved_name, triage["priority"], triage["summary"], created_at),
        )
        row = db.execute("SELECT * FROM reports WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return report_dict(row)


@app.patch("/api/reports/{report_id}")
def update_status(report_id: int, payload: dict):
    status = payload.get("status")
    if status not in STATUSES:
        raise HTTPException(422, "Choose a valid status.")
    with connect() as db:
        cursor = db.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
        if cursor.rowcount == 0:
            raise HTTPException(404, "Report not found.")
        row = db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return report_dict(row)
