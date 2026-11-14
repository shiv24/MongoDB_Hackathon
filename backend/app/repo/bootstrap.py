"""Idempotent demo workspace bootstrap for the single-user hackathon UI."""

from app.db import get_db


DEFAULT_USER = {
    "_id": "alice",
    "name": "Alice",
    "team_id": "team_a",
    "project_ids": ["lumen-signup"],
    "role": "publisher",
}

DEFAULT_PROJECT = {
    "_id": "lumen-signup",
    "team_id": "team_a",
    "name": "Lumen web app: account signup",
}


def ensure_demo_workspace() -> dict[str, bool]:
    """Create the fixed demo identity and project only when they do not exist."""
    db = get_db()
    user = db.users.update_one(
        {"_id": DEFAULT_USER["_id"]},
        {"$setOnInsert": DEFAULT_USER},
        upsert=True,
    )
    project = db.projects.update_one(
        {"_id": DEFAULT_PROJECT["_id"]},
        {"$setOnInsert": DEFAULT_PROJECT},
        upsert=True,
    )
    return {"user_created": user.upserted_id is not None, "project_created": project.upserted_id is not None}
