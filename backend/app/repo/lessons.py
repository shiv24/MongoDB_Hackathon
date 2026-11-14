"""The ONLY module that reads or writes `lessons`. Every query goes through repo.scope."""
from datetime import timedelta

from app import config
from app.agent import embed
from app.db import get_db, new_id, now
from app.errors import Forbidden, NotFound
from app.repo import events, scope
from app.repo._vector import vector_search


def _public(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "embedding"}


def _expiry(at=None) -> dict:
    at = at or now()
    exp = at + timedelta(days=config.EXPIRY_DAYS)
    return {"expires_at": exp, "purge_at": exp + timedelta(days=config.PURGE_GRACE_DAYS)}


def _visible(session: dict, doc: dict | None) -> bool:
    """May this user see this lesson at all? (Same rules as scope.lesson_filter, minus status.)"""
    if not doc or doc["team_id"] != session["team_id"]:
        return False
    if doc["scope"] == "personal" or doc["status"] == "proposed":
        return doc["owner_id"] == session["user_id"]
    if doc["scope"] == "team":
        return True
    return doc["project_id"] in session["project_ids"]


def get(session: dict, lesson_id: str) -> dict:
    doc = get_db().lessons.find_one({"_id": lesson_id})
    if not _visible(session, doc):
        raise NotFound(f"lesson {lesson_id} not found")
    return doc


def can_publish(session: dict, scope_name: str, project_id: str) -> bool:
    if scope_name not in config.LESSON_SCOPES:
        raise ValueError(f"scope must be one of {config.LESSON_SCOPES}")
    if scope_name == "team":
        return session["role"] in config.TEAM_PUBLISH_ROLES
    return project_id in session["project_ids"]


# ---------- reads ----------

def search(session: dict, project_id: str, query_embedding: list[float],
           limit: int = config.RETRIEVE_LIMIT) -> list[dict]:
    """Approved lessons this user may use for this project. Expiry is swept first."""
    expire_due(session["team_id"])
    hits = vector_search(get_db().lessons, "lessons_vector", query_embedding,
                         scope.lesson_filter(session, project_id), limit)
    return _confirm_current(session, hits)


def _confirm_current(session: dict, hits: list[dict]) -> list[dict]:
    """The search index syncs asynchronously, so re-check status against the collection itself."""
    if not hits:
        return hits
    live = {d["_id"]: d for d in get_db().lessons.find({"_id": {"$in": [h["_id"] for h in hits]}},
                                                       {"embedding": 0})}
    return [{**live[h["_id"]], "score": h["score"]} for h in hits if h["_id"] in live and live[h["_id"]]["status"] == "approved"
            and _visible(session, live[h["_id"]]) and live[h["_id"]].get("expires_at", now()) > now()]


def list_for(session: dict, project_id: str, status: str | None = None) -> list[dict]:
    scope.require_project(session, project_id)
    expire_due(session["team_id"])
    q = {"team_id": session["team_id"],
         "$or": [{"scope": "team", "status": {"$ne": "proposed"}},
                 {"scope": "project", "project_id": project_id, "status": {"$ne": "proposed"}},
                 {"owner_id": session["user_id"], "project_id": project_id}]}
    if status:
        q["status"] = status
    return [_public(d) for d in get_db().lessons.find(q).sort("created_at", -1)]


def similar_approved(session: dict, project_id: str, query_embedding: list[float], limit: int = 5) -> list[dict]:
    expire_due(session["team_id"])
    return _confirm_current(session, vector_search(get_db().lessons, "lessons_vector", query_embedding,
                                                   scope.lesson_filter(session, project_id), limit))


def current_state(session: dict, lesson_id: str) -> dict | None:
    """Pre-execution recheck: current status/revision, or None if gone or no longer visible."""
    doc = get_db().lessons.find_one({"_id": lesson_id}, {"embedding": 0})
    if doc and doc.get("expires_at") and doc["expires_at"] <= now():
        expire_due(session["team_id"])
        doc = get_db().lessons.find_one({"_id": lesson_id}, {"embedding": 0})
    if not _visible(session, doc):
        return None
    return doc


# ---------- lifecycle (every change logs a memory_event) ----------

def propose(session: dict, project_id: str, text: str, evidence_run_id: str, feedback_id: str,
            task_tags: list[str], duplicate_of: str | None, conflicts: list[dict]) -> dict:
    scope.require_project(session, project_id)
    doc = {"_id": new_id(), "team_id": session["team_id"], "project_id": project_id,
           "owner_id": session["user_id"], "scope": "personal", "text": text, "revision": 1, "supersedes": None,
           "status": "proposed", "evidence_run_id": evidence_run_id, "feedback_id": feedback_id,
           "task_tags": task_tags, "model": config.ELEVENLABS_AGENT_LLM, "approved_by": None,
           "duplicate_of": duplicate_of, "conflicts": conflicts,
           "embedding": embed.document(text), "created_at": now()}
    get_db().lessons.insert_one(doc)
    events.log_event("lesson", doc["_id"], doc["team_id"], "proposed", session["user_id"], f"feedback:{feedback_id}",
                     after={"text": text, "evidence_run_id": evidence_run_id})
    return _public(doc)


def approve(session: dict, lesson_id: str, scope_name: str, text: str | None = None) -> dict:
    doc = get(session, lesson_id)
    if doc["status"] != "proposed":
        raise ValueError(f"lesson is {doc['status']}, not proposed")
    if not can_publish(session, scope_name, doc["project_id"]):
        raise Forbidden(f"you may not publish lessons at {scope_name} scope")
    update = {"status": "approved", "scope": scope_name, "approved_by": session["user_id"],
              "approved_at": now(), "last_used_at": None, **_expiry()}
    if text and text.strip() and text.strip() != doc["text"]:
        update.update({"text": text.strip(), "embedding": embed.document(text.strip())})
    get_db().lessons.update_one({"_id": lesson_id}, {"$set": update})
    events.log_event("lesson", lesson_id, doc["team_id"], "approved", session["user_id"], "user",
                     before={"status": "proposed", "text": doc["text"]},
                     after={"status": "approved", "scope": scope_name, "text": update.get("text", doc["text"])})
    return _public(get_db().lessons.find_one({"_id": lesson_id}))


def reject(session: dict, lesson_id: str) -> dict:
    doc = get(session, lesson_id)
    if doc["status"] != "proposed":
        raise ValueError(f"lesson is {doc['status']}, not proposed")
    get_db().lessons.update_one({"_id": lesson_id}, {"$set": {"status": "rejected"}})
    events.log_event("lesson", lesson_id, doc["team_id"], "rejected", session["user_id"], "user",
                     before={"status": "proposed"}, after={"status": "rejected"})
    return _public(get_db().lessons.find_one({"_id": lesson_id}))


def _require_editor(session: dict, doc: dict) -> None:
    if doc["status"] != "approved":
        raise ValueError(f"lesson is {doc['status']}; only approved lessons can be changed")
    if not can_publish(session, doc["scope"], doc["project_id"]):
        raise Forbidden(f"you may not change {doc['scope']}-scope lessons")
    if doc["scope"] == "personal" and doc["owner_id"] != session["user_id"]:
        raise Forbidden("personal lessons can only be changed by their owner")


def correct(session: dict, lesson_id: str, new_text: str) -> dict:
    old = get(session, lesson_id)
    _require_editor(session, old)
    db = get_db()
    new = {**{k: v for k, v in old.items() if k not in ("_id", "embedding")},
           "_id": new_id(), "text": new_text, "revision": old["revision"] + 1, "supersedes": old["_id"],
           "approved_by": session["user_id"], "approved_at": now(), "embedding": embed.document(new_text),
           "created_at": now(), **_expiry()}
    db.lessons.insert_one(new)
    db.lessons.update_one({"_id": old["_id"]}, {"$set": {"status": "superseded", "superseded_by": new["_id"]}})
    events.log_event("lesson", old["_id"], old["team_id"], "superseded", session["user_id"], "correction",
                     before={"text": old["text"], "revision": old["revision"]},
                     after={"superseded_by": new["_id"]})
    events.log_event("lesson", new["_id"], new["team_id"], "corrected", session["user_id"], "correction",
                     after={"text": new_text, "revision": new["revision"], "supersedes": old["_id"]})
    return _public(new)


def retire(session: dict, lesson_id: str) -> dict:
    doc = get(session, lesson_id)
    _require_editor(session, doc)
    get_db().lessons.update_one({"_id": lesson_id}, {"$set": {"status": "retired"}})
    events.log_event("lesson", lesson_id, doc["team_id"], "retired", session["user_id"], "user",
                     before={"status": "approved"}, after={"status": "retired"})
    return _public(get_db().lessons.find_one({"_id": lesson_id}))


def forget(session: dict, lesson_id: str) -> dict:
    """Remove from future use. Runs that cited it are marked stale. The event carries no text.

    This is not complete erasure: briefs and artifacts already generated may still contain derived text.
    """
    doc = get(session, lesson_id)
    if doc["status"] == "proposed":
        if doc["owner_id"] != session["user_id"]:
            raise Forbidden("only the proposer can discard a proposed lesson")
    elif not can_publish(session, doc["scope"], doc["project_id"]):
        raise Forbidden(f"you may not forget {doc['scope']}-scope lessons")
    db = get_db()
    db.lessons.delete_one({"_id": lesson_id})
    stale = db.runs.update_many({"team_id": doc["team_id"], "provenance.id": lesson_id},
                                {"$set": {"status": "stale", "stale_reason": "a cited lesson was forgotten"}})
    events.log_event("lesson", lesson_id, doc["team_id"], "forgotten", session["user_id"], "user",
                     before={"status": doc["status"], "scope": doc["scope"], "revision": doc["revision"]},
                     after={"runs_marked_stale": stale.modified_count})
    return {"forgotten": lesson_id, "runs_marked_stale": stale.modified_count}


def mark_used(lesson_ids: list[str]) -> None:
    """Citing a lesson in an exported brief keeps it fresh."""
    if lesson_ids:
        get_db().lessons.update_many({"_id": {"$in": lesson_ids}, "status": "approved", "expires_at": {"$gt": now()}},
                                     {"$set": {"last_used_at": now(), **_expiry()}})


def expire_due(team_id: str) -> list[str]:
    """Mark approved lessons past expires_at as "expired" and log each (cause "ttl").

    Reads also filter on status, so expired lessons are excluded immediately. The TTL index on
    purge_at deletes them later; TTL alone is insufficient because it runs in the background.
    """
    db = get_db()
    due = list(db.lessons.find({"team_id": team_id, "status": "approved", "expires_at": {"$lt": now()}},
                               {"_id": 1, "expires_at": 1}))
    for d in due:
        res = db.lessons.update_one({"_id": d["_id"], "status": "approved"}, {"$set": {"status": "expired"}})
        if res.modified_count:
            events.log_event("lesson", d["_id"], team_id, "expired", "system", "ttl",
                             before={"status": "approved", "expires_at": d["expires_at"]},
                             after={"status": "expired"})
    return [d["_id"] for d in due]
