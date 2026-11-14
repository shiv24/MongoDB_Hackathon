from fastapi import APIRouter, Request

router = APIRouter(prefix="/lessons")


@router.get("")
def list_lessons(request: Request, project_id: str, status: str = "approved"):
    raise NotImplementedError


@router.post("/{lesson_id}/approve")
def approve(request: Request, lesson_id: str, body: dict):
    # TODO: {scope, text?}; team scope requires publish permission
    raise NotImplementedError


@router.post("/{lesson_id}/reject")
def reject(request: Request, lesson_id: str):
    raise NotImplementedError


@router.post("/{lesson_id}/correct")
def correct(request: Request, lesson_id: str, body: dict):
    raise NotImplementedError


@router.post("/{lesson_id}/retire")
def retire(request: Request, lesson_id: str):
    raise NotImplementedError


@router.delete("/{lesson_id}")
def forget(request: Request, lesson_id: str):
    raise NotImplementedError
