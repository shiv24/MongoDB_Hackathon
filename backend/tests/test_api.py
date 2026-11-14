"""End-to-end HTTP flow with Claude and $vectorSearch stubbed (no network, no Atlas)."""
import pytest
from fastapi.testclient import TestClient

from app.agent import brief as brief_mod
from app.agent import intent as intent_mod
from app.agent import learn, llm, validate
from app.main import app
from app.repo import context, lessons

SPEC = "Required fields: work email, full name, password."


@pytest.fixture
def client(db, monkeypatch):
    db.users.insert_many([
        {"_id": "alice", "name": "Alice", "team_id": "team_a", "project_ids": ["signup"], "role": "publisher"},
        {"_id": "carol", "name": "Carol", "team_id": "team_b", "project_ids": ["orbit"], "role": "admin"}])
    db.projects.insert_many([{"_id": "signup", "team_id": "team_a", "name": "Signup"},
                             {"_id": "orbit", "team_id": "team_b", "name": "Orbit"}])
    db.sources.insert_one({"_id": "c1", "team_id": "team_a", "project_id": "signup", "source_id": "spec",
                           "title": "Signup spec", "kind": "spec", "revision": 1, "chunk_index": 0, "text": SPEC,
                           "added_by": "alice"})

    # $vectorSearch stand-ins that still apply team/project/status rules
    monkeypatch.setattr(context, "search_sources", lambda s, p, v, limit=6: [
        {**d, "score": 0.9} for d in db.sources.find({"team_id": s["team_id"], "project_id": p})])
    monkeypatch.setattr(context, "search_decisions", lambda s, p, v, limit=6: [
        {**d, "score": 0.9} for d in db.decisions.find({"team_id": s["team_id"], "project_id": p, "status": "current"})])

    def fake_lessons(s, p, v, limit=6):
        lessons.expire_due(s["team_id"])
        return [{**d, "score": 0.8} for d in db.lessons.find({"team_id": s["team_id"], "status": "approved"})
                if lessons._visible(s, d)]
    monkeypatch.setattr(lessons, "search", fake_lessons)
    monkeypatch.setattr(lessons, "similar_approved", fake_lessons)

    def fake_parse(system, user, schema, effort="medium", max_tokens=16000):
        if schema is intent_mod.Intent:
            req = next(l for l in user.splitlines() if l.startswith("Request:")).lower()
            q = None if ("Clarification" in user or "signup" in req) else "Signup or login page?"
            return schema(feature="Signup page", documents=["Signup spec"], clarifying_question=q,
                          search_query="signup page"), "stub"
        if schema is brief_mod.BriefOut:
            prefs = [{"text": t.split(": ", 1)[1], "sources": [t[1:3]]} for t in user.splitlines()
                     if t.startswith("[L") and "preference" in t]
            return schema(objective="Build the signup page",
                          requirements=[{"text": "Collect work email, full name, password", "sources": ["S1"]}],
                          current_decisions=[], implementation_context=[], preferences=prefs,
                          acceptance_checks=[{"text": "Form has an email field", "sources": ["S1"]}],
                          open_questions=[], assumptions=[]), "stub"
        if schema is validate.Review:
            return schema(checks=[{"index": 0, "result": "passed", "evidence": "input type=email"}]), "stub"
        if schema is learn.Proposal:
            return schema(reusable=True, lesson="Always include a mobile layout below 600px.",
                          task_tags=["signup"], duplicate_of=None, conflicts=[]), "stub"
        raise AssertionError(schema)

    monkeypatch.setattr(llm, "parse", fake_parse)
    monkeypatch.setattr(llm, "generate_text", lambda s, u, **k: (
        '<!doctype html><html><head><meta name="viewport" content="width=device-width"></head>'
        '<body><input type="email"><script>bad()</script></body></html>', "stub"))
    return TestClient(app)


def test_requires_login(client):
    assert client.get("/api/projects").status_code == 401


def test_full_flow_feedback_becomes_lesson_in_next_run(client, db):
    assert client.post("/api/login", json={"user_id": "alice"}).json()["team_id"] == "team_a"

    # ambiguous request -> one clarifying question
    r = client.post("/api/runs", json={"project_id": "signup", "request": "build the page from that doc"}).json()
    assert r["status"] == "needs_clarification" and r["question"]
    r = client.post(f"/api/runs/{r['_id']}/clarify", json={"answer": "the signup page"}).json()
    assert r["status"] == "draft" and r["brief"]["requirements"][0]["sources"] == ["S1"]

    md = client.get(f"/api/runs/{r['_id']}/export").text
    assert "[S1]" in md and "## Provenance" in md

    r = client.post(f"/api/runs/{r['_id']}/execute").json()
    assert r["status"] == "executed" and "<script" not in r["artifact"]["html"]
    results = {c["name"]: c["result"] for c in r["checks"]}
    assert results["No scripts in generated output"] == "failed"  # visible, not hidden
    assert results["Form has an email field"] == "passed"

    fb = client.post(f"/api/runs/{r['_id']}/feedback", json={"text": "we always need a mobile layout"}).json()
    lesson = fb["proposed"]
    assert lesson["status"] == "proposed"

    # not used until approved
    r2 = client.post("/api/runs", json={"project_id": "signup", "request": "build the signup page"}).json()
    assert not r2["brief"]["preferences"]

    a = client.post(f"/api/lessons/{lesson['_id']}/approve", json={"scope": "project"}).json()
    assert a["status"] == "approved"

    r3 = client.post("/api/runs", json={"project_id": "signup", "request": "build the signup page"}).json()
    assert [p["text"] for p in r3["brief"]["preferences"]] == ["Always include a mobile layout below 600px."]
    cited = [e for e in r3["provenance"] if e["type"] == "lesson"]
    assert cited[0]["id"] == lesson["_id"] and cited[0]["revision"] == 1

    # retire it -> executing the old brief is refused with the change shown
    client.post(f"/api/lessons/{lesson['_id']}/retire")
    resp = client.post(f"/api/runs/{r3['_id']}/execute")
    assert resp.status_code == 409 and resp.json()["changes"][0]["change"] == "now retired"
    r3 = client.post(f"/api/runs/{r3['_id']}/refresh").json()
    assert not r3["brief"]["preferences"] and r3["status"] == "draft"

    hist = [e["event"] for e in client.get(f"/api/lessons/{lesson['_id']}/history").json()]
    assert hist == ["proposed", "approved", "retired"]


def test_other_team_cannot_read_runs_or_projects(client):
    client.post("/api/login", json={"user_id": "alice"})
    run = client.post("/api/runs", json={"project_id": "signup", "request": "build the signup page"}).json()
    client.post("/api/login", json={"user_id": "carol"})
    assert client.get(f"/api/runs/{run['_id']}").status_code == 404
    assert client.post("/api/runs", json={"project_id": "signup", "request": "x signup"}).status_code == 403
    assert client.get("/api/projects/signup/context").status_code == 403
