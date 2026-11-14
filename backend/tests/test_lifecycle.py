"""Governance lifecycle against an in-memory database: approval, scope, correction, expiry, forgetting."""
from datetime import timedelta

import pytest

from app.agent.recheck import recheck
from app.db import now
from app.errors import Forbidden, NotFound
from app.repo import context, lessons, runs

from conftest import ALICE, BOB, CAROL


def _propose(session, text="Always include a mobile layout below 600px.", project="signup"):
    return lessons.propose(session, project, text, "run1", "fb1", ["signup"], None, [])


def _events(db, record_id):
    return [e["event"] for e in db.memory_events.find({"record_id": record_id}).sort("at", 1)]


def test_proposed_lesson_is_private_to_proposer(db):
    l = _propose(BOB)
    assert l["status"] == "proposed"
    with pytest.raises(NotFound):
        lessons.get(ALICE, l["_id"])
    assert all(x["_id"] != l["_id"] for x in lessons.list_for(ALICE, "signup"))
    assert _events(db, l["_id"]) == ["proposed"]


def test_member_cannot_publish_team_scope_but_publisher_can(db):
    l = _propose(BOB)
    with pytest.raises(Forbidden):
        lessons.approve(BOB, l["_id"], "team")
    approved = lessons.approve(BOB, l["_id"], "project")
    assert approved["status"] == "approved" and approved["scope"] == "project"
    assert approved["approved_by"] == "bob" and approved["expires_at"] > now()

    l2 = _propose(ALICE, "Use sentence case everywhere.")
    assert lessons.approve(ALICE, l2["_id"], "team")["scope"] == "team"


def test_team_lessons_visible_across_projects_in_team_only(db):
    l = _propose(ALICE, project="billing")
    lessons.approve(ALICE, l["_id"], "team")
    assert lessons.get(BOB, l["_id"])  # bob isn't in billing, but team scope reaches him
    with pytest.raises(NotFound):
        lessons.get(CAROL, l["_id"])


def test_personal_lesson_invisible_to_teammates(db):
    l = _propose(ALICE)
    lessons.approve(ALICE, l["_id"], "personal")
    with pytest.raises(NotFound):
        lessons.get(BOB, l["_id"])


def test_correct_creates_revision_and_supersedes(db):
    l = lessons.approve(ALICE, _propose(ALICE)["_id"], "project")
    new = lessons.correct(ALICE, l["_id"], "Include a mobile layout below 640px.")
    assert new["revision"] == 2 and new["supersedes"] == l["_id"]
    assert db.lessons.find_one({"_id": l["_id"]})["status"] == "superseded"
    assert _events(db, l["_id"]) == ["proposed", "approved", "superseded"]
    assert _events(db, new["_id"]) == ["corrected"]


def test_member_cannot_retire_team_lesson(db):
    l = lessons.approve(ALICE, _propose(ALICE)["_id"], "team")
    with pytest.raises(Forbidden):
        lessons.retire(BOB, l["_id"])
    assert lessons.retire(ALICE, l["_id"])["status"] == "retired"


def test_expire_due_marks_and_logs_before_ttl(db):
    l = lessons.approve(ALICE, _propose(ALICE)["_id"], "project")
    db.lessons.update_one({"_id": l["_id"]}, {"$set": {"expires_at": now() - timedelta(minutes=1)}})
    assert lessons.expire_due("team_a") == [l["_id"]]
    doc = db.lessons.find_one({"_id": l["_id"]})
    assert doc["status"] == "expired" and doc["purge_at"] > now()  # TTL purge comes later
    ev = db.memory_events.find_one({"record_id": l["_id"], "event": "expired"})
    assert ev["cause"] == "ttl" and ev["actor"] == "system"
    assert lessons.expire_due("team_a") == []  # idempotent


def test_forget_marks_citing_runs_stale_and_logs_without_text(db):
    l = lessons.approve(ALICE, _propose(ALICE)["_id"], "project")
    run = runs.create(ALICE, "signup", "build signup", status="executed",
                      provenance=[{"key": "L1", "type": "lesson", "id": l["_id"], "revision": 1, "text": l["text"]}])
    out = lessons.forget(ALICE, l["_id"])
    assert out["runs_marked_stale"] == 1
    assert db.lessons.find_one({"_id": l["_id"]}) is None
    assert db.runs.find_one({"_id": run["_id"]})["status"] == "stale"
    ev = db.memory_events.find_one({"record_id": l["_id"], "event": "forgotten"})
    assert "text" not in (ev["before"] or {}) and "text" not in (ev["after"] or {})


def test_memory_events_never_updated_or_deleted_by_app_code():
    import pathlib
    for p in pathlib.Path(__file__).resolve().parents[1].joinpath("app").rglob("*.py"):
        src = p.read_text()
        for bad in ("memory_events.update", "memory_events.delete", "memory_events.replace", "memory_events.find_one_and"):
            assert bad not in src, f"{p} mutates memory_events"


def test_recheck_detects_superseded_decision_and_retired_lesson(db):
    d = context.add_decision(ALICE, "signup", "Use Lumen ID.")
    l = lessons.approve(ALICE, _propose(ALICE)["_id"], "project")
    run = {"brief": {"requirements": [{"text": "x", "sources": ["D1", "L1"]}], "current_decisions": [],
                     "implementation_context": [], "preferences": [], "acceptance_checks": [], "open_questions": []},
           "provenance": [{"key": "D1", "type": "decision", "id": d["_id"], "revision": 1},
                          {"key": "L1", "type": "lesson", "id": l["_id"], "revision": 1}]}
    assert recheck(ALICE, run) == []
    context.supersede_decision(ALICE, d["_id"], "Use Lumen ID v2.")
    lessons.retire(ALICE, l["_id"])
    changes = {c["key"]: c["change"] for c in recheck(ALICE, run)}
    assert changes == {"D1": "superseded", "L1": "now retired"}


def test_decision_and_run_reads_are_team_scoped(db):
    d = context.add_decision(ALICE, "signup", "Use Lumen ID.")
    with pytest.raises(NotFound):
        context.get_decision(CAROL, d["_id"])
    run = runs.create(ALICE, "signup", "build signup", status="draft")
    with pytest.raises(NotFound):
        runs.get(CAROL, run["_id"])
