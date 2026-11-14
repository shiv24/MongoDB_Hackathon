"""Append-only writer for memory_events. Never update or delete here.

A "forgotten" event must not contain the forgotten text.
"""
from app.db import get_db, new_id, now


def log_event(record_type: str, record_id: str, team_id: str, event: str, actor: str, cause: str,
              before: dict | None = None, after: dict | None = None) -> None:
    get_db().memory_events.insert_one({
        "_id": new_id(), "record_type": record_type, "record_id": record_id, "team_id": team_id,
        "event": event, "actor": actor, "cause": cause, "before": before, "after": after, "at": now(),
    })


def history(team_id: str, record_id: str) -> list[dict]:
    return list(get_db().memory_events.find({"team_id": team_id, "record_id": record_id}).sort("at", 1))
