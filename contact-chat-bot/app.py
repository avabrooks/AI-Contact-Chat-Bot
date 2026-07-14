"""
FastAPI backend for the Contact Chat Bot ("who do I contact about this?").

Fully local: contacts.json and rooms.json live on disk and you edit them by
hand. The only outbound network call is to the Anthropic API to classify
issue text. Meeting scheduling generates a downloadable .ics file -- it does
NOT connect to any real calendar system, so there's nothing to authorize or
upload.

Run:
    pip install -r requirements.txt
    uvicorn app:app --reload --port 8001

Then open http://localhost:8001
"""

import os
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import secrets

from router_engine import classify, suggested_time_slots, list_rooms, generate_ics

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Contact Chat Bot")
security = HTTPBasic()

AUTH_USER = os.environ.get("BOT_USER", "employee")
AUTH_PASS = os.environ.get("BOT_PASS", "changeme")


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username, AUTH_USER)
    ok_pass = secrets.compare_digest(credentials.password, AUTH_PASS)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class RouteRequest(BaseModel):
    issue: str


class ScheduleRequest(BaseModel):
    contact_name: str
    contact_email: str
    subject: str
    slot_iso: str          # ISO datetime string, one of the values returned by /api/slots
    duration_minutes: int = 30
    location: str = ""
    requester_name: str
    requester_email: str


@app.get("/")
def index(user: str = Depends(require_auth)):
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.post("/api/route")
def route(req: RouteRequest, user: str = Depends(require_auth)):
    if not req.issue or not req.issue.strip():
        raise HTTPException(status_code=400, detail="issue is required")
    result = classify(req.issue.strip())
    result["suggested_slots"] = [dt.isoformat() for dt in suggested_time_slots()]
    return result


@app.get("/api/rooms")
def rooms(min_capacity: int = 1, user: str = Depends(require_auth)):
    return list_rooms(min_capacity)


@app.post("/api/schedule")
def schedule(req: ScheduleRequest, user: str = Depends(require_auth)):
    try:
        start_dt = datetime.fromisoformat(req.slot_iso)
    except ValueError:
        raise HTTPException(status_code=400, detail="slot_iso must be an ISO datetime string")

    ics_text = generate_ics(
        subject=req.subject,
        start_dt=start_dt,
        duration_minutes=req.duration_minutes,
        organizer_name=req.requester_name,
        organizer_email=req.requester_email,
        attendee_name=req.contact_name,
        attendee_email=req.contact_email,
        location=req.location,
        description=f"Scheduled via the internal Contact Chat Bot regarding: {req.subject}",
    )
    return Response(
        content=ics_text,
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="meeting_invite.ics"'},
    )


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
