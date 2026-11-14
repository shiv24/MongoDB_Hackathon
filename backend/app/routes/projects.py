from fastapi import APIRouter, Request

router = APIRouter(prefix="/projects")


@router.get("")
def list_projects(request: Request):
    # TODO: projects from session["project_ids"]
    raise NotImplementedError


@router.get("/{project_id}/context")
def get_context(request: Request, project_id: str):
    # TODO: sources, current decisions, approved lessons visible to this user, with owner/scope/revision
    raise NotImplementedError


@router.post("/{project_id}/sources")
def add_source(request: Request, project_id: str, body: dict):
    raise NotImplementedError


@router.post("/{project_id}/decisions")
def add_decision(request: Request, project_id: str, body: dict):
    raise NotImplementedError


@router.post("/decisions/{decision_id}/supersede")
def supersede_decision(request: Request, decision_id: str, body: dict):
    raise NotImplementedError
