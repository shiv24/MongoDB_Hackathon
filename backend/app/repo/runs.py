"""Runs: request, brief, cited context revisions, model, artifact, check results. Plus feedback."""
from app.db import get_db, new_id, now
from app.errors import NotFound
from app.repo import scope


def create(session: dict, project_id: str, request_text: str, **fields) -> dict:
    scope.require_project(session, project_id)
    doc = {"_id": new_id(), "team_id": session["team_id"], "project_id": project_id,
           "user_id": session["user_id"], "request": request_text, "created_at": now(), **fields}
    get_db().runs.insert_one(doc)
    return doc


def get(session: dict, run_id: str) -> dict:
    doc = get_db().runs.find_one({"_id": run_id, "team_id": session["team_id"]})
    if not doc or doc["project_id"] not in session["project_ids"] or doc["user_id"] != session["user_id"]:
        raise NotFound(f"run {run_id} not found")
    return doc


def update(session: dict, run_id: str, fields: dict) -> dict:
    get(session, run_id)
    get_db().runs.update_one({"_id": run_id}, {"$set": {**fields, "updated_at": now()}})
    return get(session, run_id)


def recent(session: dict, project_id: str, limit: int = 20) -> list[dict]:
    scope.require_project(session, project_id)
    return list(get_db().runs.find({"team_id": session["team_id"], "project_id": project_id, "user_id": session["user_id"]},
                                   {"request": 1, "status": 1, "created_at": 1, "user_id": 1})
                .sort("created_at", -1).limit(limit))


def add_feedback(session: dict, run: dict, text: str) -> dict:
    doc = {"_id": new_id(), "team_id": run["team_id"], "project_id": run["project_id"], "run_id": run["_id"],
           "user_id": session["user_id"], "text": text, "proposed_lesson_id": None, "created_at": now()}
    get_db().feedback.insert_one(doc)
    return doc


def link_feedback_lesson(feedback_id: str, lesson_id: str | None) -> None:
    get_db().feedback.update_one({"_id": feedback_id}, {"$set": {"proposed_lesson_id": lesson_id}})
