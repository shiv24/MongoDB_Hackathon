"""ElevenLabs Speech-to-Text for the voice request. Audio is forwarded, never stored."""
import httpx

from app import config

URL = "https://api.elevenlabs.io/v1/speech-to-text"


def transcribe(audio: bytes, filename: str, content_type: str) -> str:
    if not config.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    resp = httpx.post(
        URL,
        headers={"xi-api-key": config.ELEVENLABS_API_KEY},
        data={"model_id": config.ELEVENLABS_STT_MODEL},
        files={"file": (filename or "audio.webm", audio, content_type or "audio/webm")},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("text", "").strip()
