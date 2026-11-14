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

from fastapi import UploadFile, File

@router.post('/transcribe')
async def transcribe(request: Request, audio: UploadFile = File(...)):
    current(request)
    if not config.ELEVENLABS_API_KEY:
        raise RuntimeError('Set ELEVENLABS_API_KEY for microphone transcription. Typed requests remain available.')
    content = await audio.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise ValueError('Audio must be between 1 byte and 10 MB.')
    async with httpx.AsyncClient(timeout=45) as client:
        try:
            response = await client.post('https://api.elevenlabs.io/v1/speech-to-text', headers={'xi-api-key':config.ELEVENLABS_API_KEY}, data={'model_id':config.ELEVENLABS_STT_MODEL}, files={'file':(audio.filename or 'recording.webm', content, audio.content_type or 'audio/webm')})
            response.raise_for_status()
        except httpx.HTTPError:
            raise RuntimeError('ElevenLabs transcription failed. Check key, quota and connection, or type your request.') from None
    return {'text':response.json()['text']}
