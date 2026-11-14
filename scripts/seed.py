"""Seed curated demo fixtures (scripts/data/fixtures.json) into Atlas.

team_a exercises every lifecycle state; team_b exists to verify isolation. All fixture text was
written for this hackathon. Usage (repo root):  python scripts/seed.py [--reset]
"""
import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config  # noqa: E402
from app.agent import embed  # noqa: E402
from app.db import get_db, now  # noqa: E402
from app.repo import events  # noqa: E402
from app.repo.context import chunk  # noqa: E402

DATA = Path(__file__).parent / "data" / "fixtures.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="delete existing documents first (keeps indexes)")
    args = ap.parse_args()
    db = get_db()
    fx = json.loads(DATA.read_text())

    if args.reset:
        for c in ["users", "projects", "sources", "decisions", "lessons", "runs", "feedback"]:
            db[c].delete_many({})
        # memory_events is append-only for the app; a reset is a deliberate demo wipe by an operator.
        db.memory_events.delete_many({})
        print("reset done")

    db.users.insert_many(fx["users"])
    db.projects.insert_many(fx["projects"])
    t = now()

    # sources: chunk + embed
    src_docs = []
    for s in fx["sources"]:
        pieces = chunk(s["text"])
        vecs = embed.documents([f"{s['title']}\n\n{p}" for p in pieces])
        for i, (p, v) in enumerate(zip(pieces, vecs)):
            src_docs.append({"_id": f"{s['source_id']}-r{s.get('revision', 1)}-c{i}", "team_id": s["team_id"],
                             "project_id": s["project_id"], "source_id": s["source_id"], "title": s["title"],
                             "kind": s.get("kind", "spec"), "revision": s.get("revision", 1), "chunk_index": i,
                             "text": p, "embedding": v, "added_by": s["added_by"], "created_at": t})
    db.sources.insert_many(src_docs)

    # decisions
    dvecs = embed.documents([d["text"] for d in fx["decisions"]])
    for d, v in zip(fx["decisions"], dvecs):
        db.decisions.insert_one({**d, "embedding": v, "created_at": t})
        events.log_event("decision", d["_id"], d["team_id"], "created", "seed", "fixture",
                         after={"text": d["text"], "revision": d["revision"]})
        if d["status"] == "superseded":
            events.log_event("decision", d["_id"], d["team_id"], "superseded", "seed", "fixture",
                             after={"superseded_by": d.get("superseded_by")})

    # lessons
    lvecs = embed.documents([l["text"] for l in fx["lessons"]])
    for l, v in zip(fx["lessons"], lvecs):
        days = l.pop("expires_in_days", config.EXPIRY_DAYS)
        exp = t + timedelta(days=days)
        doc = {"revision": 1, "supersedes": None, "evidence_run_id": None, "feedback_id": None,
               "task_tags": [], "model": config.CLAUDE_MODEL, "duplicate_of": None, "conflicts": [],
               "approved_by": l["owner_id"] if l["status"] != "proposed" else None,
               **l, "embedding": v, "created_at": t,
               "expires_at": exp, "purge_at": exp + timedelta(days=config.PURGE_GRACE_DAYS)}
        db.lessons.insert_one(doc)
        events.log_event("lesson", l["_id"], l["team_id"], "proposed" if l["status"] == "proposed" else "approved",
                         "seed", "fixture", after={"text": l["text"], "scope": l["scope"], "status": l["status"]})
        if l["status"] == "retired":
            events.log_event("lesson", l["_id"], l["team_id"], "retired", "seed", "fixture",
                             after={"status": "retired"})

    print(f"seeded {len(fx['users'])} users, {len(fx['projects'])} projects, {len(src_docs)} source chunks, "
          f"{len(fx['decisions'])} decisions, {len(fx['lessons'])} lessons")


if __name__ == "__main__":
    main()
