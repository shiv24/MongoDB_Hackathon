"""ElevenLabs Speech-to-Text client for the voice brief.

POST https://api.elevenlabs.io/v1/speech-to-text
  header  xi-api-key: ELEVENLABS_API_KEY
  form    file=<audio>, model_id=ELEVENLABS_STT_MODEL
Check the current ElevenLabs docs for the model id and response shape before implementing.
"""


async def transcribe(audio: bytes, filename: str, content_type: str) -> str:
    # TODO(P1): httpx.AsyncClient POST, return response JSON "text"; do not persist audio
    raise NotImplementedError
