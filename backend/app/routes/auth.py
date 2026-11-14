from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/login")
def login(request: Request, user_id: str):
    # TODO: look up demo user; request.session = {user_id, team_id, project_ids, role}
    raise NotImplementedError
