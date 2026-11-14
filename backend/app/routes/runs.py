from fastapi import APIRouter, Request

router = APIRouter(prefix="/runs")


@router.post("")
def create_run(request: Request, body: dict):
    # TODO: {project_id, request} -> intent -> retrieve -> brief. May return a clarifying question.
    raise NotImplementedError


@router.get("/{run_id}")
def get_run(request: Request, run_id: str):
    raise NotImplementedError


@router.patch("/{run_id}/brief")
def edit_brief(request: Request, run_id: str, body: dict):
    # TODO: user edits or answers open questions
    raise NotImplementedError


@router.get("/{run_id}/export")
def export_brief(request: Request, run_id: str):
    # TODO: Markdown brief with citations, for another coding tool
    raise NotImplementedError


@router.post("/{run_id}/execute")
def execute(request: Request, run_id: str):
    # TODO: recheck memory revisions -> model -> artifact + validation evidence
    raise NotImplementedError


@router.post("/{run_id}/feedback")
def feedback(request: Request, run_id: str, body: dict):
    # TODO: store feedback -> proposed lesson (not yet approved)
    raise NotImplementedError
