"""Idempotent Atlas setup: collections, memory_events validator, indexes, Vector Search, TTL.

Run from the repo root:  python scripts/setup_atlas.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from pymongo import ASCENDING, DESCENDING  # noqa: E402
from pymongo.errors import CollectionInvalid, OperationFailure  # noqa: E402
from pymongo.operations import SearchIndexModel  # noqa: E402

from app import config  # noqa: E402
from app.db import get_db  # noqa: E402

COLLECTIONS = ["users", "projects", "sources", "decisions", "lessons", "runs", "feedback", "memory_events"]

MEMORY_EVENTS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["record_type", "record_id", "team_id", "event", "actor", "cause", "at"],
        "properties": {
            "record_type": {"enum": ["lesson", "decision", "source"]},
            "record_id": {"bsonType": "string"},
            "team_id": {"bsonType": "string"},
            "event": {"enum": ["created", "proposed", "approved", "rejected", "corrected", "superseded",
                               "retired", "expired", "forgotten", "scope_changed"]},
            "actor": {"bsonType": "string"},
            "cause": {"bsonType": "string"},
            "at": {"bsonType": "date"},
        },
    }
}


def vector_index(name, filters):
    return name, {"fields": [{"type": "vector", "path": "embedding", "numDimensions": config.EMBED_DIMS,
                              "similarity": "cosine"}] + [{"type": "filter", "path": f} for f in filters]}


VECTOR_INDEXES = {
    "sources": vector_index("sources_vector", ["team_id", "project_id"]),
    "decisions": vector_index("decisions_vector", ["team_id", "project_id", "status"]),
    "lessons": vector_index("lessons_vector", ["team_id", "project_id", "owner_id", "scope", "status"]),
}


def main():
    db = get_db()
    existing = set(db.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            try:
                if name == "memory_events":
                    db.create_collection(name, validator=MEMORY_EVENTS_SCHEMA, validationLevel="strict")
                else:
                    db.create_collection(name)
                print(f"created collection {name}")
            except CollectionInvalid:
                pass
    db.command("collMod", "memory_events", validator=MEMORY_EVENTS_SCHEMA, validationLevel="strict")
    print("memory_events validator set")

    db.users.create_index("team_id")
    db.projects.create_index("team_id")
    db.sources.create_index([("team_id", ASCENDING), ("source_id", ASCENDING), ("revision", DESCENDING)])
    db.decisions.create_index([("team_id", ASCENDING), ("project_id", ASCENDING), ("status", ASCENDING)])
    db.lessons.create_index([("team_id", ASCENDING), ("expires_at", ASCENDING)])
    db.lessons.create_index([("team_id", ASCENDING), ("project_id", ASCENDING), ("status", ASCENDING)])
    db.lessons.create_index("purge_at", expireAfterSeconds=0)  # TTL purge only; the app sweep logs expiry first
    db.runs.create_index([("team_id", ASCENDING), ("project_id", ASCENDING), ("created_at", DESCENDING)])
    db.runs.create_index("provenance.id")
    db.feedback.create_index("run_id")
    db.memory_events.create_index([("record_id", ASCENDING), ("at", ASCENDING)])
    print("regular + TTL indexes ensured")

    for coll, (name, definition) in VECTOR_INDEXES.items():
        current = {i["name"]: i for i in db[coll].list_search_indexes()}
        try:
            if name in current:
                db[coll].update_search_index(name, definition)
                print(f"updated search index {coll}.{name}")
            else:
                db[coll].create_search_index(SearchIndexModel(definition=definition, name=name, type="vectorSearch"))
                print(f"creating search index {coll}.{name}")
        except OperationFailure as exc:
            print(f"!! could not create {coll}.{name}: {exc.details.get('errmsg', exc)}")
            print("   If the sandbox tier caps search indexes, see skills/atlas-setup (merge decisions+lessons).")

    print("waiting for search indexes to be READY", end="", flush=True)
    for _ in range(90):
        statuses = {}
        for coll, (name, _) in VECTOR_INDEXES.items():
            for i in db[coll].list_search_indexes(name):
                statuses[f"{coll}.{name}"] = i.get("status")
        if statuses and all(s == "READY" for s in statuses.values()) and len(statuses) == len(VECTOR_INDEXES):
            print("\nall search indexes READY:", statuses)
            return
        print(".", end="", flush=True)
        time.sleep(5)
    print("\nnot READY yet:", statuses, "- re-run later or check the Atlas UI")


if __name__ == "__main__":
    main()
