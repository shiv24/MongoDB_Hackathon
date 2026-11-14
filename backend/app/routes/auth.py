from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.repo import users
from app.session import current

router = APIRouter()


class Login(BaseModel):
    user_id: str


@router.get("/users")
def demo_users():
    return users.demo_users()


@router.post("/login")
def login(request: Request, body: Login):
    u = users.get(body.user_id)  # team and projects come from the database, never from the client
    request.session.clear()
    request.session.update({"user_id": u["_id"], "name": u["name"], "team_id": u["team_id"],
                            "project_ids": u["project_ids"], "role": u["role"]})
    return current(request)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    return current(request)
