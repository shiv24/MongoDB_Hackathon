from fastapi import APIRouter, Request

router = APIRouter(prefix="/lessons")


@router.get("")
def list_lessons(request: Request):
    # TODO(P2): team lessons by score, grouped by status
    raise NotImplementedError


@router.patch("/{lesson_id}")
def edit_lesson(request: Request, lesson_id: str, body: dict):
    # TODO(P2): admin only - edit text (re-embed) or mark wrong; log memory_event
    raise NotImplementedError


@router.delete("/{lesson_id}")
def forget_lesson(request: Request, lesson_id: str):
    # TODO(P2): admin only - hard delete; log 'forgotten' event without text
    raise NotImplementedError
