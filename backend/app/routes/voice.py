from fastapi import APIRouter, Request, UploadFile

from app import config
from app.agent import stt
from app.session import current

router = APIRouter()


@router.post("/transcribe")
async def transcribe(request: Request, audio: UploadFile):
    current(request)
    data = await audio.read(config.MAX_AUDIO_BYTES + 1)
    if len(data) > config.MAX_AUDIO_BYTES:
        raise ValueError("audio too large (max 10 MB)")
    return {"text": stt.transcribe(data, audio.filename, audio.content_type)}
