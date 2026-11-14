from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.repo import context, events, lessons, runs, users
from app.session import current

router = APIRouter(prefix="/projects")


class SourceIn(BaseModel):
    title: str
    text: str
    kind: str = "spec"


class DecisionIn(BaseModel):
    text: str


@router.get("")
def list_projects(request: Request):
    return users.projects_for(current(request))


@router.get("/{project_id}/context")
def get_context(request: Request, project_id: str):
    s = current(request)
    return {
        "sources": context.list_sources(s, project_id),
        "decisions": context.list_decisions(s, project_id, include_superseded=True),
        "lessons": lessons.list_for(s, project_id),
        "runs": runs.recent(s, project_id),
    }


@router.post("/{project_id}/sources")
def add_source(request: Request, project_id: str, body: SourceIn):
    return context.add_source(current(request), project_id, body.title, body.text, body.kind)


@router.post("/{project_id}/decisions")
def add_decision(request: Request, project_id: str, body: DecisionIn):
    return context.add_decision(current(request), project_id, body.text)


@router.post("/decisions/{decision_id}/supersede")
def supersede_decision(request: Request, decision_id: str, body: DecisionIn):
    return context.supersede_decision(current(request), decision_id, body.text)


@router.get("/decisions/{decision_id}/history")
def decision_history(request: Request, decision_id: str):
    s = current(request)
    context.get_decision(s, decision_id)
    return events.history(s["team_id"], decision_id)
