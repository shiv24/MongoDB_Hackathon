from fastapi import Request

from app.errors import NotLoggedIn


def current(request: Request) -> dict:
    """Identity and membership come from the signed session cookie only."""
    s = request.session
    if not s.get("user_id"):
        raise NotLoggedIn("log in first (POST /login)")
    return {"user_id": s["user_id"], "team_id": s["team_id"], "project_ids": list(s.get("project_ids", [])),
            "role": s.get("role", "member"), "name": s.get("name", s["user_id"])}
