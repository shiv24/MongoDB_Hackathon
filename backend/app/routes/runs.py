from fastapi import APIRouter, Request

router = APIRouter(prefix="/runs")


@router.post("")
def create_run(request: Request, body: dict):
    # TODO(P1/P3): {brief, memory} -> retrieve, condense, generate A/B in parallel, score
    raise NotImplementedError


@router.get("/{run_id}")
def get_run(request: Request, run_id: str):
    # TODO: run detail incl. used_lessons and token savings
    raise NotImplementedError


@router.post("/{run_id}/vote")
def vote(request: Request, run_id: str, body: dict):
    # TODO(P2): {winner, reasons} -> insert vote, update lessons, return deltas
    raise NotImplementedError
