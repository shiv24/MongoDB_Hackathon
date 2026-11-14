"""Idempotent demo workspace bootstrap for the single-user hackathon UI."""

from app.db import get_db


DEFAULT_USER = {
    "_id": "console-alice",
    "name": "Alice",
    "team_id": "console-team",
    "project_ids": ["admin-console"],
    "role": "publisher",
}

DEFAULT_PROJECT = {
    "_id": "admin-console",
    "team_id": "console-team",
    "name": "Admin console",
}


def ensure_demo_workspace() -> dict[str, bool]:
    """Create the fixed demo identity and project only when they do not exist."""
    db = get_db()
    user = db.users.update_one(
        {"_id": DEFAULT_USER["_id"]},
        {"$setOnInsert": DEFAULT_USER},
        upsert=True,
    )
    db.users.update_one({'_id': 'console-bob'}, {'$setOnInsert': {
        '_id': 'console-bob', 'name': 'Bob', 'team_id': DEFAULT_USER['team_id'],
        'project_ids': DEFAULT_USER['project_ids'], 'role': 'member'}}, upsert=True)
    project = db.projects.update_one(
        {"_id": DEFAULT_PROJECT["_id"]},
        {"$setOnInsert": DEFAULT_PROJECT},
        upsert=True,
    )
    # Older sources had no scope; they belonged to their original project.
    db.sources.update_many({"scope": {"$exists": False}}, {"$set": {"scope": "project"}})
    return {"user_created": user.upserted_id is not None, "project_created": project.upserted_id is not None}
