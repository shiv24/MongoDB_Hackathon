"""Starts an ElevenLabs agent conversation for the logged-in user."""
import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import config
from app.agent import pipeline
from app.repo import agent_sessions, runs
from app.session import current

router = APIRouter(prefix="/voice")


class SessionIn(BaseModel):
    project_id: str


@router.post("/session")
def start(request: Request, body: SessionIn):
    s = current(request)
    p = pipeline.project(s, body.project_id)
    if not (config.ELEVENLABS_API_KEY and config.ELEVENLABS_AGENT_ID):
        raise RuntimeError("ELEVENLABS_API_KEY / ELEVENLABS_AGENT_ID not set - run scripts/setup_elevenlabs_agent.py")
    resp = httpx.get("https://api.elevenlabs.io/v1/convai/conversation/get-signed-url",
                     params={"agent_id": config.ELEVENLABS_AGENT_ID},
                     headers={"xi-api-key": config.ELEVENLABS_API_KEY}, timeout=15)
    resp.raise_for_status()
    sid, token = agent_sessions.mint(s, body.project_id)
    return {"agent_session_id": sid, "signed_url": resp.json()["signed_url"],
            "dynamic_variables": {"secret__pf_token": token, "user_name": s["name"], "project_name": p["name"]}}


@router.get("/session/{agent_session_id}/run")
def current_run(request: Request, agent_session_id: str):
    s = current(request)
    row = agent_sessions.get_for_user(s, agent_session_id)
    return runs.get(s, row["current_run_id"]) if row["current_run_id"] else None
