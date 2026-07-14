"""
Claude-powered "who do I talk to about this?" router.

Everything here is 100% local:
  - contacts.json / rooms.json are plain files you edit by hand.
  - The only network call is to the Anthropic API to classify the issue
    text (department/person match + suggested meeting times).
  - "Scheduling" does not touch any real calendar. It generates a
    standard .ics calendar-invite file that gets downloaded to your
    computer, which you then send yourself (attach to an email, drag into
    Outlook/Google Calendar, etc). No data is uploaded anywhere else.
"""

import json
import os
import uuid
from datetime import datetime, timedelta, time

from anthropic import Anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
BASE_DIR = os.path.dirname(__file__)

_client = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = Anthropic(api_key=api_key)
    return _client


def load_contacts():
    with open(os.path.join(BASE_DIR, "contacts.json")) as f:
        return json.load(f)["contacts"]


def load_rooms():
    with open(os.path.join(BASE_DIR, "rooms.json")) as f:
        return json.load(f)["rooms"]


ROUTE_SYSTEM_PROMPT = """You are an internal "who do I contact?" assistant for a company.
You are given a directory of contacts (name, department, role, and the kinds of issues they handle)
and an employee's plain-text description of their issue.

Pick the single best contact for this issue. If truly nothing in the directory is a good match,
say so honestly instead of forcing a guess.

Respond with ONLY a JSON object, no markdown fences, no extra text, in this exact shape:
{
  "department": "<department name or null>",
  "contact_name": "<best contact's name, or null if no good match>",
  "contact_email": "<their email, or null>",
  "confidence": "<high|medium|low>",
  "reasoning": "<one sentence explaining the match>"
}
"""


def classify(issue_text: str) -> dict:
    contacts = load_contacts()
    client = _get_client()
    directory_text = json.dumps(contacts, indent=2)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=ROUTE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Directory:\n{directory_text}\n\nEmployee's issue:\n{issue_text}",
            }
        ],
    )
    raw = resp.content[0].text.strip().strip("`")
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "department": None,
            "contact_name": None,
            "contact_email": None,
            "confidence": "low",
            "reasoning": "Could not parse a confident match. Try rephrasing, or check contacts.json covers this topic.",
        }
    return result


def suggested_time_slots(count=3, business_hour_choices=(10, 14)):
    """Purely local heuristic: next few weekdays at standard hours.
    Not tied to anyone's real calendar (no calendar integration is connected)."""
    slots = []
    d = datetime.now() + timedelta(days=1)
    while len(slots) < count:
        if d.weekday() < 5:  # Mon-Fri
            for hour in business_hour_choices:
                if len(slots) >= count:
                    break
                slots.append(datetime.combine(d.date(), time(hour, 0)))
        d += timedelta(days=1)
    return slots


def list_rooms(min_capacity: int = 1):
    return [r for r in load_rooms() if r["capacity"] >= min_capacity]


def generate_ics(
    subject: str,
    start_dt: datetime,
    duration_minutes: int,
    organizer_name: str,
    organizer_email: str,
    attendee_name: str,
    attendee_email: str,
    location: str = "",
    description: str = "",
) -> str:
    """Builds a standard .ics file as text. The caller writes/serves this file;
    nothing is sent anywhere automatically."""
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    fmt = "%Y%m%dT%H%M%S"
    uid = f"{uuid.uuid4()}@internal-router"
    dtstamp = datetime.utcnow().strftime(fmt) + "Z"

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Internal Contact Router//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART:{start_dt.strftime(fmt)}
DTEND:{end_dt.strftime(fmt)}
SUMMARY:{subject}
DESCRIPTION:{description}
LOCATION:{location}
ORGANIZER;CN={organizer_name}:mailto:{organizer_email}
ATTENDEE;CN={attendee_name};RSVP=TRUE:mailto:{attendee_email}
STATUS:CONFIRMED
SEQUENCE:0
END:VEVENT
END:VCALENDAR
"""
    return ics
