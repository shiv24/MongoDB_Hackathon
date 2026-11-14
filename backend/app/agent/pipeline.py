"""Orchestrates request -> intent -> retrieve -> brief -> (review) -> execute -> feedback."""
from app.agent import brief as brief_mod
from app.agent import execute as exec_mod
from app.agent import intent as intent_mod
from app.agent import learn, retrieve, validate
from app.db import get_db, now
from app.errors import Conflict, NotFound
from app.repo import context, lessons, runs, scope


def _project(session: dict, project_id: str) -> dict:
    scope.require_project(session, project_id)
    p = get_db().projects.find_one({"_id": project_id, "team_id": session["team_id"]})
    if not p:
        raise NotFound(f"project {project_id} not found")
    return p


def _resolve(session, project_id, request, clarification=None):
    project = _project(session, project_id)
    titles = [s["title"] for s in context.list_sources(session, project_id)]
    decisions = [d["text"] for d in context.list_decisions(session, project_id)]
    intent, model = intent_mod.resolve(project, titles, decisions, request, clarification)
    return intent.model_dump(), model


def _build(session, project_id, request, intent, answers=None) -> dict:
    entries = retrieve.gather(session, project_id, intent["search_query"] or request)
    brief, model = brief_mod.assemble(request, intent, entries, answers)
    blocking = [q for q in brief["open_questions"] if q["blocking"] and not q.get("answer")]
    return {"intent": intent, "provenance": entries, "brief": brief, "answers": answers or [],
            "status": "needs_answers" if blocking else "draft", "models": {"brief": model}}


def create(session: dict, project_id: str, request: str) -> dict:
    request = request.strip()
    if not request:
        raise ValueError("request is empty")
    intent, model = _resolve(session, project_id, request)
    if intent["clarifying_question"]:
        return runs.create(session, project_id, request, intent=intent, status="needs_clarification",
                           question=intent["clarifying_question"], models={"intent": model})
    fields = _build(session, project_id, request, intent)
    fields["models"]["intent"] = model
    return runs.create(session, project_id, request, **fields)


def clarify(session: dict, run_id: str, answer: str) -> dict:
    run = runs.get(session, run_id)
    if run["status"] != "needs_clarification":
        raise ValueError("this run is not waiting for a clarification")
    intent, model = _resolve(session, run["project_id"], run["request"], answer)
    fields = _build(session, run["project_id"], run["request"], intent)
    fields["models"]["intent"] = model
    fields["clarification"] = {"question": run["question"], "answer": answer}
    return runs.update(session, run_id, fields)


def answer_questions(session: dict, run_id: str, answers: list[dict]) -> dict:
    """answers: [{index, answer}] for brief.open_questions. Rebuilds the brief with the answers."""
    run = runs.get(session, run_id)
    qs = run["brief"]["open_questions"]
    merged = list(run.get("answers", []))
    for a in answers:
        i = a["index"]
        if not 0 <= i < len(qs) or not a.get("answer", "").strip():
            raise ValueError(f"bad answer for question {i}")
        merged.append({"question": qs[i]["text"], "answer": a["answer"].strip()})
    new_brief, model = brief_mod.assemble(run["request"], run["intent"], run["provenance"], merged)
    blocking = [q for q in new_brief["open_questions"] if q["blocking"] and not q.get("answer")]
    return runs.update(session, run_id, {"brief": new_brief, "answers": merged,
                                         "status": "needs_answers" if blocking else "draft",
                                         "models.brief": model})


def edit_brief(session: dict, run_id: str, brief: dict) -> dict:
    run = runs.get(session, run_id)
    if run["status"] in ("needs_clarification",):
        raise ValueError("answer the clarifying question first")
    required = ("objective", "requirements", "current_decisions", "implementation_context", "preferences",
                "acceptance_checks", "open_questions", "assumptions")
    missing = [k for k in required if k not in brief]
    if missing:
        raise ValueError(f"brief is missing {missing}")
    checked = brief_mod.validate_citations(brief, run["provenance"])
    blocking = [q for q in checked["open_questions"] if q.get("blocking") and not q.get("answer")]
    return runs.update(session, run_id, {"brief": checked, "edited_by": session["user_id"],
                                         "status": "needs_answers" if blocking else "draft"})


def refresh(session: dict, run_id: str) -> dict:
    """Re-retrieve current context and rebuild the brief (after a decision/lesson changed)."""
    run = runs.get(session, run_id)
    fields = _build(session, run["project_id"], run["request"], run["intent"], run.get("answers"))
    fields["models"]["intent"] = run.get("models", {}).get("intent")
    fields["previous"] = {"provenance": run.get("provenance"), "refreshed_at": now()}
    fields["stale_reason"] = None
    return runs.update(session, run_id, fields)


def export(session: dict, run_id: str) -> str:
    run = runs.get(session, run_id)
    if "brief" not in run:
        raise ValueError("no brief yet")
    if run["status"] == "draft":
        runs.update(session, run_id, {"status": "exported", "exported_at": now()})
    return brief_mod.to_markdown(run)


def execute(session: dict, run_id: str) -> dict:
    run = runs.get(session, run_id)
    if "brief" not in run:
        raise ValueError("no brief yet")
    blocking = [q["text"] for q in run["brief"]["open_questions"] if q.get("blocking") and not q.get("answer")]
    if blocking:
        raise Conflict("resolve blocking questions before running", {"blocking_questions": blocking})
    changes = exec_mod.recheck(session, run)
    if changes:
        runs.update(session, run_id, {"status": "stale", "stale_reason": "cited context changed", "changes": changes})
        raise Conflict("cited context changed since this brief was prepared; refresh the brief", {"changes": changes})

    html, model, notes = exec_mod.generate(run)
    checks = validate.static_checks(html, notes)
    reviewed, review_model = validate.review(html, run["brief"]["acceptance_checks"])
    lesson_ids = [e["id"] for e in run["provenance"]
                  if e["type"] == "lesson" and e["key"] in brief_mod.cited_keys(run["brief"])]
    lessons.mark_used(lesson_ids)
    return runs.update(session, run_id, {
        "status": "executed", "executed_at": now(), "artifact": {"type": "html", "html": html},
        "checks": checks + reviewed, "models.execute": model, "models.review": review_model, "changes": [],
    })


def feedback(session: dict, run_id: str, text: str) -> dict:
    if not text.strip():
        raise ValueError("feedback is empty")
    run = runs.get(session, run_id)
    fb = runs.add_feedback(session, run, text.strip())
    result = learn.propose(session, run, fb)
    runs.link_feedback_lesson(fb["_id"], (result.get("proposed") or {}).get("_id"))
    return {"feedback": fb, **result}
