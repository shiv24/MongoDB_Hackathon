from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.agent import pipeline
from app.repo import runs
from app.session import current

router = APIRouter(prefix="/runs")


class BriefIn(BaseModel):
    brief: dict


class CheckResult(BaseModel):
    index: int
    result: str
    evidence: str | None = None


class OutcomeIn(BaseModel):
    results: list[CheckResult]
    tool: str | None = None
    notes: str | None = None


class FeedbackIn(BaseModel):
    text: str
    lesson: str | None = None


@router.get("/{run_id}")
def get_run(request: Request, run_id: str):
    return runs.get(current(request), run_id)


@router.patch("/{run_id}/brief")
def edit_brief(request: Request, run_id: str, body: BriefIn):
    return pipeline.edit_brief(current(request), run_id, body.brief)


@router.get("/{run_id}/export", response_class=PlainTextResponse)
def export_brief(request: Request, run_id: str):
    return PlainTextResponse(pipeline.export(current(request), run_id), media_type="text/markdown")


@router.post("/{run_id}/outcome")
def record_outcome(request: Request, run_id: str, body: OutcomeIn):
    return pipeline.record_outcome(current(request), run_id, [r.model_dump() for r in body.results], body.tool, body.notes)


@router.post("/{run_id}/feedback")
def feedback(request: Request, run_id: str, body: FeedbackIn):
    return pipeline.feedback(current(request), run_id, body.text, body.lesson)
