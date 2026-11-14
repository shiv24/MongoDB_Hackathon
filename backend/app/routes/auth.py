from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/login")
def login(request: Request, user_id: str):
    # TODO(P2): look up user, set request.session = {user_id, team_id, role}
    raise NotImplementedError
