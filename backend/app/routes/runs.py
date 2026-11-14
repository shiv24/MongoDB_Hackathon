from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.agent import pipeline
from app.repo import runs
from app.session import current

router = APIRouter(prefix="/runs")


class RunIn(BaseModel):
    project_id: str
    request: str


class Clarify(BaseModel):
    answer: str


class Answer(BaseModel):
    index: int
    answer: str


class Answers(BaseModel):
    answers: list[Answer]


class BriefIn(BaseModel):
    brief: dict


class FeedbackIn(BaseModel):
    text: str


@router.post("")
def create_run(request: Request, body: RunIn):
    return pipeline.create(current(request), body.project_id, body.request)


@router.get("/{run_id}")
def get_run(request: Request, run_id: str):
    return runs.get(current(request), run_id)


@router.post("/{run_id}/clarify")
def clarify(request: Request, run_id: str, body: Clarify):
    return pipeline.clarify(current(request), run_id, body.answer)


@router.post("/{run_id}/answers")
def answer(request: Request, run_id: str, body: Answers):
    return pipeline.answer_questions(current(request), run_id, [a.model_dump() for a in body.answers])


@router.patch("/{run_id}/brief")
def edit_brief(request: Request, run_id: str, body: BriefIn):
    return pipeline.edit_brief(current(request), run_id, body.brief)


@router.post("/{run_id}/refresh")
def refresh(request: Request, run_id: str):
    return pipeline.refresh(current(request), run_id)


@router.get("/{run_id}/export", response_class=PlainTextResponse)
def export_brief(request: Request, run_id: str):
    return PlainTextResponse(pipeline.export(current(request), run_id), media_type="text/markdown")


@router.post("/{run_id}/execute")
def execute(request: Request, run_id: str):
    return pipeline.execute(current(request), run_id)


@router.post("/{run_id}/feedback")
def feedback(request: Request, run_id: str, body: FeedbackIn):
    return pipeline.feedback(current(request), run_id, body.text)
