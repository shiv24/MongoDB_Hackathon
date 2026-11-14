from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.repo import events, lessons
from app.session import current

router = APIRouter(prefix="/lessons")


class Approve(BaseModel):
    scope: str
    text: str | None = None


class Correct(BaseModel):
    text: str


@router.get("")
def list_lessons(request: Request, project_id: str, status: str | None = None):
    return lessons.list_for(current(request), project_id, status)


@router.post("/{lesson_id}/approve")
def approve(request: Request, lesson_id: str, body: Approve):
    return lessons.approve(current(request), lesson_id, body.scope, body.text)


@router.post("/{lesson_id}/reject")
def reject(request: Request, lesson_id: str):
    return lessons.reject(current(request), lesson_id)


@router.post("/{lesson_id}/correct")
def correct(request: Request, lesson_id: str, body: Correct):
    return lessons.correct(current(request), lesson_id, body.text)


@router.post("/{lesson_id}/retire")
def retire(request: Request, lesson_id: str):
    return lessons.retire(current(request), lesson_id)


@router.delete("/{lesson_id}")
def forget(request: Request, lesson_id: str):
    return lessons.forget(current(request), lesson_id)


@router.get("/{lesson_id}/history")
def history(request: Request, lesson_id: str):
    s = current(request)
    lessons.get(s, lesson_id)
    return events.history(s["team_id"], lesson_id)
