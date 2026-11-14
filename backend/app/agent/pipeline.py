"""The ElevenLabs agent drafts through tools; the user exports the brief to their coding tool.

  agent: get_project_context -> start_draft     scoped retrieval (Voyage + Atlas), run created
  agent: save_brief          -> save_brief      cited brief, citations validated
  user:  export              -> export          recheck cited memory; stale -> refused with the change
  user:  record result       -> record_outcome  which acceptance checks passed, as outcome evidence
  agent or UI: feedback      -> feedback        proposed lesson; approval is a separate, explicit step
Every step is traced to LangSmith when LANGSMITH_TRACING=true.
"""
from langsmith import traceable

from app import config
from app.agent import brief as brief_mod
from app.agent import embed, retrieve
from app.agent.recheck import recheck
from app.db import get_db, now
from app.errors import Conflict, NotFound
from app.repo import context, lessons, runs, scope

CHECK_RESULTS = ("passed", "failed", "not_run")


def project(session: dict, project_id: str) -> dict:
    scope.require_project(session, project_id)
    p = get_db().projects.find_one({"_id": project_id, "team_id": session["team_id"]})
    if not p:
        raise NotFound(f"project {project_id} not found")
    return p


@traceable(name="promptforge.start_draft")
def start_draft(session: dict, project_id: str, request: str, search_query: str | None = None,
                conversation_id: str | None = None) -> dict:
    request = (request or "").strip()
    if not request:
        raise ValueError("request is empty")
    p = project(session, project_id)
    entries = retrieve.gather(session, project_id, (search_query or request).strip())
    run = runs.create(session, project_id, request, status="drafting", provenance=entries,
                      intent={"feature": request, "search_query": search_query or request},
                      author={"kind": "elevenlabs_agent", "conversation_id": conversation_id})
    return {"run": run, "project": p, "sources": [s["title"] for s in context.list_sources(session, project_id)],
            "context": brief_mod.context_block(entries)}


@traceable(name="promptforge.save_brief")
def save_brief(session: dict, run_id: str, payload: dict) -> dict:
    run = runs.get(session, run_id)
    if run["status"] in ("exported", "reviewed"):
        raise ValueError("this brief was already exported; start a new request")
    brief = brief_mod.validate_citations(brief_mod.from_agent(payload), run["provenance"])
    answers = brief_mod.parse_resolved(payload.get("resolved_questions"))
    feature = (payload.get("feature") or "").strip() or run["intent"]["feature"]
    blocking = [q for q in brief["open_questions"] if q["blocking"]]
    return runs.update(session, run_id, {
        "brief": brief, "answers": answers, "intent.feature": feature,
        "status": "needs_answers" if blocking else "draft", "stale_reason": None, "changes": [],
        "brief_revision": run.get("brief_revision", 0) + 1})


def edit_brief(session: dict, run_id: str, brief: dict) -> dict:
    run = runs.get(session, run_id)
    required = ("objective", "requirements", "current_decisions", "implementation_context", "preferences",
                "acceptance_checks", "open_questions", "assumptions")
    missing = [k for k in required if k not in brief]
    if missing:
        raise ValueError(f"brief is missing {missing}")
    checked = brief_mod.validate_citations(brief, run["provenance"])
    blocking = [q for q in checked["open_questions"] if q.get("blocking") and not q.get("answer")]
    return runs.update(session, run_id, {"brief": checked, "edited_by": session["user_id"],
                                         "status": "needs_answers" if blocking else "draft"})


@traceable(name="promptforge.export")
def export(session: dict, run_id: str) -> str:
    """Recheck cited memory, then hand out the Markdown brief (for Claude Code or any coding tool)."""
    run = runs.get(session, run_id)
    if "brief" not in run:
        raise ValueError("no brief yet")
    blocking = [q["text"] for q in run["brief"]["open_questions"] if q.get("blocking") and not q.get("answer")]
    if blocking:
        raise Conflict("resolve blocking questions before exporting", {"blocking_questions": blocking})
    changes = recheck(session, run)
    if changes:
        runs.update(session, run_id, {"status": "stale", "stale_reason": "cited context changed", "changes": changes})
        raise Conflict("cited context changed since this brief was prepared; ask the agent to redo it",
                       {"changes": changes})
    if run["status"] in ("draft", "stale"):
        runs.update(session, run_id, {"status": "exported", "exported_at": now()})
    cited = brief_mod.cited_keys(run["brief"])
    lessons.mark_used([e["id"] for e in run["provenance"] if e["type"] == "lesson" and e["key"] in cited])
    return brief_mod.to_markdown(run)


@traceable(name="promptforge.record_outcome")
def record_outcome(session: dict, run_id: str, results: list[dict], tool: str | None = None,
                   notes: str | None = None) -> dict:
    """User-reported validation of the externally built result. Unreported checks stay not_run."""
    run = runs.get(session, run_id)
    checks = run.get("brief", {}).get("acceptance_checks", [])
    by_index = {r["index"]: r for r in results}
    recorded = []
    for i, c in enumerate(checks):
        r = by_index.get(i, {})
        result = r.get("result", "not_run")
        if result not in CHECK_RESULTS:
            raise ValueError(f"result must be one of {CHECK_RESULTS}")
        recorded.append({"name": c["text"], "sources": c.get("sources", []), "result": result,
                         "method": "user_review", "evidence": (r.get("evidence") or "").strip()})
    return runs.update(session, run_id, {"checks": recorded, "status": "reviewed",
                                         "outcome": {"tool": tool, "notes": notes, "by": session["user_id"],
                                                     "at": now()}})


@traceable(name="promptforge.feedback")
def feedback(session: dict, run_id: str, text: str, lesson_text: str | None,
             task_tags: list[str] | None = None, conflict_keys: list[str] | None = None) -> dict:
    """Store feedback; if a reusable lesson was stated, propose it (never approve here)."""
    if not (text or "").strip():
        raise ValueError("feedback is empty")
    run = runs.get(session, run_id)
    fb = runs.add_feedback(session, run, text.strip())
    lesson_text = (lesson_text or "").strip()
    if not lesson_text:
        return {"feedback_id": fb["_id"], "proposed": None, "reason": "no reusable lesson stated"}

    similar = lessons.similar_approved(session, run["project_id"], embed.query(lesson_text))
    dup = similar[0]["_id"] if similar and similar[0]["score"] >= config.DUPLICATE_SCORE else None
    prov = {e["key"]: e for e in run.get("provenance", [])}
    conflicts = [{"key": k, "type": prov[k]["type"], "id": prov[k]["id"], "text": prov[k]["text"]}
                 for k in conflict_keys or [] if k in prov and prov[k]["type"] in ("decision", "lesson")]
    lesson = lessons.propose(session, run["project_id"], lesson_text, run_id, fb["_id"], task_tags or [], dup, conflicts)
    runs.link_feedback_lesson(fb["_id"], lesson["_id"])
    allowed = [s for s in config.LESSON_SCOPES if lessons.can_publish(session, s, run["project_id"])]
    return {"feedback_id": fb["_id"], "proposed": lesson, "duplicate_of": dup, "scopes_allowed": allowed}
