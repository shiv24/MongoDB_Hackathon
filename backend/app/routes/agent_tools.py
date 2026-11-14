"""Webhook tools for the ElevenLabs agent. The agent's LLM never supplies identity:
every call carries X-PF-Session (the secret__pf_token dynamic variable, hidden from the LLM),
which maps to the logged-in user's session. All governance runs in app/repo as usual."""
import hmac

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from app import config
from app.agent import pipeline
from app.errors import NotLoggedIn
from app.repo import agent_sessions, lessons

router = APIRouter(prefix="/agent")


def _session(token: str | None, agent_key: str | None) -> dict:
    if config.AGENT_TOOL_SECRET and not hmac.compare_digest(agent_key or "", config.AGENT_TOOL_SECRET):
        raise NotLoggedIn("bad agent key")
    return agent_sessions.resolve(token)


class ContextIn(BaseModel):
    request: str = Field(description="What the user wants built, in their words")
    search_query: str | None = None
    conversation_id: str | None = None


class BriefIn(BaseModel):
    run_id: str
    feature: str | None = None
    objective: str
    requirements: list[str] = []
    current_decisions: list[str] = []
    implementation_context: list[str] = []
    preferences: list[str] = []
    acceptance_checks: list[str] = []
    blocking_questions: list[str] = []
    other_questions: list[str] = []
    assumptions: list[str] = []
    resolved_questions: list[str] = []


class FeedbackIn(BaseModel):
    run_id: str
    feedback: str
    lesson: str | None = None
    task_tags: list[str] = []
    conflicts: list[str] = []


class LessonDecision(BaseModel):
    lesson_id: str
    scope: str | None = None


@router.post("/context")
def get_project_context(body: ContextIn, x_pf_session: str | None = Header(None),
                        x_pf_agent_key: str | None = Header(None)):
    row = _session(x_pf_session, x_pf_agent_key)
    out = pipeline.start_draft(row["session"], row["project_id"], body.request, body.search_query, body.conversation_id)
    agent_sessions.set_run(row["_id"], out["run"]["_id"])
    return {"run_id": out["run"]["_id"], "project": out["project"]["name"], "project_sources": out["sources"],
            "context": out["context"],
            "instructions": "Cite keys like [S1], [D2], [L1] in brief items. Only these keys exist."}


@router.post("/brief")
def save_brief(body: BriefIn, x_pf_session: str | None = Header(None), x_pf_agent_key: str | None = Header(None)):
    row = _session(x_pf_session, x_pf_agent_key)
    from app.repo import runs
    from app.errors import Forbidden
    if runs.get(row["session"], body.run_id)["project_id"] != row["project_id"]:
        raise Forbidden("Run belongs to another project")
    run = pipeline.save_brief(row["session"], body.run_id, body.model_dump())
    b = run["brief"]
    uncited = [i["text"] for s in ("requirements", "current_decisions", "implementation_context", "preferences")
               for i in b[s] if i.get("uncited")]
    return {"status": run["status"], "brief_revision": run["brief_revision"],
            "dropped_unknown_citations": b["citation_warnings"], "uncited_items": uncited,
            "blocking_questions": [q["text"] for q in b["open_questions"] if q["blocking"]],
            "next": "Tell the user the brief is on screen; they can export it to their coding tool."}


@router.post("/feedback")
def record_feedback(body: FeedbackIn, x_pf_session: str | None = Header(None), x_pf_agent_key: str | None = Header(None)):
    row = _session(x_pf_session, x_pf_agent_key)
    out = pipeline.feedback(row["session"], body.run_id, body.feedback, body.lesson, body.task_tags, body.conflicts)
    l = out.get("proposed")
    return {"proposed_lesson_id": l["_id"] if l else None, "lesson": l["text"] if l else None,
            "duplicate_of": out.get("duplicate_of"), "conflicts": l["conflicts"] if l else [],
            "scopes_allowed": out.get("scopes_allowed", []),
            "next": "Read the lesson back and ask who it should apply to. Approve only after an explicit yes."}


@router.post("/lessons/approve")
def approve_lesson(body: LessonDecision, x_pf_session: str | None = Header(None), x_pf_agent_key: str | None = Header(None)):
    row = _session(x_pf_session, x_pf_agent_key)
    from app.errors import Forbidden
    raise Forbidden("Approve this lesson in the app; agent tools cannot grant user consent.")


@router.post("/lessons/reject")
def reject_lesson(body: LessonDecision, x_pf_session: str | None = Header(None), x_pf_agent_key: str | None = Header(None)):
    row = _session(x_pf_session, x_pf_agent_key)
    return {"status": lessons.reject(row["session"], body.lesson_id)["status"]}
