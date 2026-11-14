"""End-to-end flow through the ElevenLabs agent tool webhooks and the UI API, with Voyage,
$vectorSearch and the ElevenLabs signed-URL call stubbed (no network, no Atlas)."""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.agent import embed
from app.main import app
from app.repo import context, lessons, scope
from app.routes import projects, voice

SPEC = "Required fields: work email, full name, password."


@pytest.fixture
def client(db, monkeypatch):
    db.users.insert_many([
        {"_id": "alice", "name": "Alice", "team_id": "team_a", "project_ids": ["signup"], "role": "admin"},
        {"_id": "bob", "name": "Bob", "team_id": "team_a", "project_ids": ["signup"], "role": "member"},
        {"_id": "carol", "name": "Carol", "team_id": "team_b", "project_ids": ["orbit"], "role": "admin"}])
    db.projects.insert_many([{"_id": "signup", "team_id": "team_a", "name": "Signup"},
                             {"_id": "orbit", "team_id": "team_b", "name": "Orbit"}])
    db.sources.insert_one({"_id": "c1", "team_id": "team_a", "project_id": "signup", "source_id": "spec",
                           "title": "Signup spec", "kind": "spec", "revision": 1, "chunk_index": 0, "text": SPEC,
                           "scope": "project", "owner_id": "alice", "added_by": "alice"})
    context.add_decision({"user_id": "alice", "team_id": "team_a", "project_ids": ["signup"], "role": "admin"},
                         "signup", "Use the Lumen ID service.")

    monkeypatch.setattr(context, "search_sources", lambda s, p, v, limit=6: [
        {**d, "score": 0.9} for d in db.sources.find(scope.source_filter(s, p)).limit(limit)])
    monkeypatch.setattr(context, "search_decisions", lambda s, p, v, limit=6: [
        {**d, "score": 0.9} for d in db.decisions.find({"team_id": s["team_id"], "project_id": p, "status": "current"})])

    def fake_lessons(s, p, v, limit=6):
        lessons.expire_due(s["team_id"])
        return [{**d, "score": 0.8} for d in db.lessons.find({"team_id": s["team_id"], "status": "approved"})
                if lessons._visible(s, d)]
    monkeypatch.setattr(lessons, "search", fake_lessons)
    monkeypatch.setattr(lessons, "similar_approved", fake_lessons)
    monkeypatch.setattr(embed, "rerank", lambda q, docs, k: [(i, 0.5) for i in range(min(k, len(docs)))])

    monkeypatch.setattr(config, "AGENT_TOOL_SECRET", "")
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test")
    monkeypatch.setattr(config, "ELEVENLABS_AGENT_ID", "agent_test")

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"signed_url": "wss://example.invalid/signed"}
    monkeypatch.setattr(voice.httpx, "get", lambda *a, **k: FakeResp())
    return TestClient(app)


def _voice_session(client, user="alice", project="signup"):
    client.post("/api/login", json={"user_id": user})
    s = client.post("/api/voice/session", json={"project_id": project}).json()
    return s, {"X-PF-Session": s["dynamic_variables"]["secret__pf_token"]}


def test_file_upload_uses_existing_scoped_ingestion(client, db, monkeypatch):
    class Page:
        def extract_text(self):
            return "PDF requirement: the signup form must work with a keyboard."

    class Reader:
        is_encrypted = False
        pages = [Page()]

        def __init__(self, _stream):
            pass

    monkeypatch.setattr(projects, "PdfReader", Reader)
    client.post("/api/login", json={"user_id": "alice"})
    response = client.post("/api/projects/signup/sources/file", data={"title": "", "text": "Uploaded by Alice.", "scope": "team"},
                           files={"file": ("accessibility.pdf", b"%PDF-1.7 test", "application/pdf")})

    assert response.status_code == 200
    assert response.json()["title"] == "accessibility"
    saved = db.sources.find_one({"project_id": "signup", "title": "accessibility"})
    assert saved["kind"] == "pdf" and saved["scope"] == "team"
    assert "keyboard" in saved["text"] and "Uploaded by Alice" in saved["text"]

    text_response = client.post("/api/projects/signup/sources/file", data={"title": "Plain notes"},
                                files={"file": ("notes.txt", b"Use the shared FormField component.", "text/plain")})
    assert text_response.status_code == 200
    text_source = db.sources.find_one({"project_id": "signup", "title": "Plain notes"})
    assert text_source["kind"] == "text" and text_source["scope"] == "project" and "FormField" in text_source["text"]

    client.post("/api/login", json={"user_id": "bob"})
    denied = client.post("/api/projects/signup/sources/file", data={"scope": "team"},
                         files={"file": ("restricted.txt", b"Private", "text/plain")})
    assert denied.status_code == 403

    client.post("/api/login", json={"user_id": "carol"})
    forbidden = client.post("/api/projects/signup/sources/file",
                            files={"file": ("other.pdf", b"%PDF-1.7 test", "application/pdf")})
    assert forbidden.status_code == 403


def test_source_scopes_are_enforced_for_reads_writes_and_retrieval(client, db, monkeypatch):
    db.projects.insert_one({"_id": "billing", "team_id": "team_a", "name": "Billing"})
    db.users.update_one({"_id": "alice"}, {"$addToSet": {"project_ids": "billing"}})
    alice = {"user_id": "alice", "team_id": "team_a", "project_ids": ["signup", "billing"], "role": "admin"}

    client.post("/api/login", json={"user_id": "alice"})
    company = client.post("/api/projects/signup/sources", json={
        "title": "Shared title", "text": "Company-wide guidance", "scope": "team"}).json()
    project = client.post("/api/projects/signup/sources", json={
        "title": "Shared title", "text": "Signup-only guidance", "scope": "project"}).json()
    personal = client.post("/api/projects/signup/sources", json={
        "title": "Private notes", "text": "Alice-only guidance", "scope": "personal"}).json()
    assert company["scope"] == "team" and company["source_id"] != project["source_id"]
    assert db.sources.find_one({"source_id": personal["source_id"]})["owner_id"] == "alice"
    assert db.memory_events.count_documents({"record_type": "source", "event": "created"}) == 3

    assert {s["source_id"] for s in context.search_sources(alice, "billing", [0.1])} >= {
        company["source_id"], personal["source_id"]}
    assert project["source_id"] not in {
        s["source_id"] for s in context.search_sources(alice, "billing", [0.1])}

    billing_ids = {s["source_id"] for s in client.get("/api/projects/billing/context").json()["sources"]}
    assert company["source_id"] in billing_ids and personal["source_id"] in billing_ids
    assert project["source_id"] not in billing_ids

    client.post("/api/login", json={"user_id": "bob"})
    bob_ids = {s["source_id"] for s in client.get("/api/projects/signup/context").json()["sources"]}
    assert company["source_id"] in bob_ids and project["source_id"] in bob_ids
    assert personal["source_id"] not in bob_ids
    for visibility in ("team", "project"):
        denied = client.post("/api/projects/signup/sources", json={
            "title": "Unauthorized", "text": "Cannot publish", "scope": visibility})
        assert denied.status_code == 403
    own = client.post("/api/projects/signup/sources", json={
        "title": "Bob's notes", "text": "Private to Bob", "scope": "personal"})
    assert own.status_code == 200
    assert own.json()["source_id"] not in {
        s["source_id"] for s in context.list_sources(alice, "signup")}

    client.post("/api/login", json={"user_id": "carol"})
    assert company["source_id"] not in {
        s["source_id"] for s in client.get("/api/projects/orbit/context").json()["sources"]}
    assert client.post("/api/projects/signup/sources", json={
        "title": "Wrong team", "text": "No access", "scope": "team"}).status_code == 403


def test_publisher_can_add_project_source_but_not_company_source(client, db):
    db.users.update_one({"_id": "bob"}, {"$set": {"role": "publisher"}})
    client.post("/api/login", json={"user_id": "bob"})
    project = client.post("/api/projects/signup/sources", json={
        "title": "Publisher notes", "text": "Project guidance", "scope": "project"})
    assert project.status_code == 200
    assert db.sources.find_one({"source_id": project.json()["source_id"]})["scope"] == "project"
    company = client.post("/api/projects/signup/sources", json={
        "title": "Company notes", "text": "Company guidance", "scope": "team"})
    assert company.status_code == 403
    assert db.sources.find_one({"title": "Company notes"}) is None


def test_tools_reject_missing_or_bad_token(client):
    assert client.post("/api/agent/context", json={"request": "x"}).status_code == 401
    assert client.post("/api/agent/context", json={"request": "x"}, headers={"X-PF-Session": "nope"}).status_code == 401


def test_voice_session_requires_login_and_membership(client):
    assert client.post("/api/voice/session", json={"project_id": "signup"}).status_code == 401
    client.post("/api/login", json={"user_id": "carol"})
    assert client.post("/api/voice/session", json={"project_id": "signup"}).status_code == 403


def test_agent_drafts_user_exports_feedback_becomes_lesson(client, db):
    s, h = _voice_session(client)
    assert s["signed_url"].startswith("wss://") and s["dynamic_variables"]["project_name"] == "Signup"

    ctx = client.post("/api/agent/context", json={"request": "build the signup page", "search_query": "signup page"}, headers=h).json()
    assert "[S1]" in ctx["context"] and "[D1]" in ctx["context"]
    run_id = ctx["run_id"]

    saved = client.post("/api/agent/brief", headers=h, json={
        "run_id": run_id, "objective": "Build the signup page",
        "requirements": ["Collect work email, full name, password [S1]"],
        "current_decisions": ["Create accounts through Lumen ID [D1]"],
        "acceptance_checks": ["Form has an email field [S1]"],
        "blocking_questions": ["What are the company size options?"]}).json()
    assert saved["status"] == "draft" and saved["blocking_questions"] == []

    # the UI polls the run the agent is working on
    assert client.get(f"/api/voice/session/{s['agent_session_id']}/run").json()["_id"] == run_id

    saved = client.post("/api/agent/brief", headers=h, json={
        "run_id": run_id, "objective": "Build the signup page",
        "requirements": ["Collect work email, full name, password [S1]"],
        "current_decisions": ["Create accounts through Lumen ID [D1]"],
        "acceptance_checks": ["Form has an email field [S1]"],
        "resolved_questions": ["What are the company size options? => 1-10, 11-50, 51+"]}).json()
    assert saved["status"] == "draft" and saved["brief_revision"] == 2

    md = client.get(f"/api/runs/{run_id}/export").text
    assert "[S1]" in md and "## Provenance" in md and "1-10, 11-50, 51+" in md

    out = client.post(f"/api/runs/{run_id}/outcome", json={"tool": "Claude Code", "results": [
        {"index": 0, "result": "passed", "evidence": "input type=email present"}]}).json()
    assert out["status"] == "reviewed" and out["checks"][0]["method"] == "user_review"

    fb = client.post("/api/agent/feedback", headers=h, json={
        "run_id": run_id, "feedback": "It broke on my phone", "lesson": "Always include a mobile layout below 600px."}).json()
    assert fb["proposed_lesson_id"] and fb["scopes_allowed"] == ["personal", "project", "team"]

    # proposed lessons do not shape new briefs
    ctx2 = client.post("/api/agent/context", json={"request": "build the signup page", "search_query": "signup"}, headers=h).json()
    assert "[L1]" not in ctx2["context"]

    assert client.post("/api/agent/lessons/approve", headers=h, json={"lesson_id": fb["proposed_lesson_id"], "scope": "project"}).status_code == 403
    ok = client.post(f"/api/lessons/{fb["proposed_lesson_id"]}/approve", json={"scope": "project"}).json()
    assert ok["status"] == "approved"
    ctx3 = client.post("/api/agent/context", json={"request": "build the signup page", "search_query": "signup"}, headers=h).json()
    assert "[L1] approved project preference rev 1: Always include a mobile layout below 600px." in ctx3["context"]

    hist = [e["event"] for e in client.get(f"/api/lessons/{fb['proposed_lesson_id']}/history").json()]
    assert hist == ["proposed", "approved"]


def test_member_agent_cannot_publish_team_lesson(client):
    s, h = _voice_session(client, user="bob")
    run_id = client.post("/api/agent/context", json={"request": "signup", "search_query": "signup"}, headers=h).json()["run_id"]
    fb = client.post("/api/agent/feedback", headers=h, json={"run_id": run_id, "feedback": "x", "lesson": "Use sentence case."}).json()
    assert "team" not in fb["scopes_allowed"]
    assert client.post("/api/agent/lessons/approve", headers=h, json={"lesson_id": fb["proposed_lesson_id"], "scope": "team"}).status_code == 403


def test_simple_ui_feedback_does_not_propose_lesson(client, db, monkeypatch):
    _, h = _voice_session(client)
    run_id = client.post("/api/agent/context", json={"request": "signup", "search_query": "signup"}, headers=h).json()["run_id"]

    from app.agent import llm
    monkeypatch.setattr(llm, "propose", lambda _text: pytest.fail("simple feedback must not propose a lesson"))
    response = client.post(f"/api/runs/{run_id}/feedback", json={
        "text": "Thumbs down: The spacing feels cramped.", "propose_lesson": False,
    })

    assert response.status_code == 200
    assert response.json()["proposed"] is None
    saved = db.feedback.find_one({"run_id": run_id})
    assert saved["text"] == "Thumbs down: The spacing feels cramped."
    assert saved["proposed_lesson_id"] is None


def test_stale_brief_refused_at_export(client, db):
    s, h = _voice_session(client)
    run_id = client.post("/api/agent/context", json={"request": "signup", "search_query": "signup"}, headers=h).json()["run_id"]
    client.post("/api/agent/brief", headers=h, json={"run_id": run_id, "objective": "o",
                                                    "requirements": ["Use Lumen ID [D1]"], "acceptance_checks": []})
    d = db.decisions.find_one({"status": "current"})
    client.post(f"/api/projects/decisions/{d['_id']}/supersede", json={"text": "Use Lumen ID v2."})
    r = client.get(f"/api/runs/{run_id}/export")
    assert r.status_code == 409 and r.json()["changes"][0]["change"] == "superseded"


def test_other_team_token_cannot_touch_run(client):
    s, h = _voice_session(client)
    run_id = client.post("/api/agent/context", json={"request": "signup", "search_query": "signup"}, headers=h).json()["run_id"]
    _, h_carol = _voice_session(client, user="carol", project="orbit")
    r = client.post("/api/agent/brief", headers=h_carol, json={"run_id": run_id, "objective": "steal", "requirements": [],
                                                               "acceptance_checks": []})
    assert r.status_code == 404
