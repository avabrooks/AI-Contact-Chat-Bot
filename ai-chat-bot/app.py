"""
FastAPI backend for the IT Asset Chatbot.

Run:
    pip install -r requirements.txt
    python seed_data.py        # one-time: creates + populates assets.db
    uvicorn app:app --reload --port 8000

Then open http://localhost:8000

Access is gated with HTTP Basic Auth (username/password from .env) as a
lightweight placeholder for "IT department only." For a real internal
rollout, put this behind your company VPN/intranet and/or SSO instead of
relying on Basic Auth alone -- see README.md.
"""

import os
import secrets

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import init_db
from nl_query import answer_question

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="IT Asset Chatbot")
security = HTTPBasic()

AUTH_USER = os.environ.get("IT_BOT_USER", "it")
AUTH_PASS = os.environ.get("IT_BOT_PASS", "changeme")


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


class ChatRequest(BaseModel):
    question: str


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def index(user: str = Depends(require_auth)):
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@app.post("/api/chat")
def chat(req: ChatRequest, user: str = Depends(require_auth)):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    result = answer_question(req.question.strip())
    return result


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
