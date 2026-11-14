from app.db import get_db
from app.errors import NotFound


def get(user_id: str) -> dict:
    u = get_db().users.find_one({"_id": user_id})
    if not u:
        raise NotFound(f"unknown user {user_id}")
    return u


def demo_users() -> list[dict]:
    """Demo login picker only: names and teams, nothing else."""
    return list(get_db().users.find({}, {"name": 1, "team_id": 1, "role": 1}))


def projects_for(session: dict) -> list[dict]:
    return list(get_db().projects.find({"team_id": session["team_id"], "_id": {"$in": session["project_ids"]}}))
