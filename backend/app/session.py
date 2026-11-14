from fastapi import Request

from app.errors import NotLoggedIn


def current(request: Request) -> dict:
    """Identity and membership come from the signed session cookie only."""
    from app.repo import users
    s = request.session
    if not s.get("user_id"):
        raise NotLoggedIn("log in first (POST /login)")
    u = users.get(s["user_id"])
    return {"user_id": u["_id"], "team_id": u["team_id"], "project_ids": u.get("project_ids", []),
            "role": u.get("role", "member"), "name": u.get("name", u["_id"])}
