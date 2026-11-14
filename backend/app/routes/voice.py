from fastapi import APIRouter, Request, UploadFile

router = APIRouter()


@router.post("/transcribe")
async def transcribe(request: Request, audio: UploadFile):
    # TODO(P1): require session; size cap (~10 MB); call agent.stt.transcribe; return {"text": ...}
    raise NotImplementedError
