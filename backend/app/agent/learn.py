"""Step 6: feedback -> proposed lesson. Nothing affects future briefs until a user approves it with a scope."""
from pydantic import BaseModel, Field

from app import config
from app.agent import embed, llm
from app.repo import context, lessons


class Proposal(BaseModel):
    reusable: bool = Field(description="False if the feedback is a one-off fix with no reusable guidance")
    lesson: str = Field(description="One imperative instruction a future brief could include; empty if not reusable")
    task_tags: list[str] = Field(description="Short tags for which tasks this applies to, e.g. signup, landing-page, forms")
    duplicate_of: str | None = Field(description="Key of an existing lesson that already says the same thing, else null")
    conflicts: list[str] = Field(description="Keys of existing lessons or decisions this would contradict")


SYSTEM = """You turn a teammate's feedback on an AI-generated result into ONE reusable lesson for future briefs.
- Write the lesson as a short imperative instruction ("Always include a mobile layout below 600px").
- Only generalize what the feedback actually says; do not add new requirements.
- Compare with the existing lessons and decisions given. Name a duplicate if one already says the same thing. List conflicts with any lesson or decision it contradicts.
- If the feedback is a one-off fix with no reusable guidance, set reusable=false."""


def propose(session: dict, run: dict, feedback: dict) -> dict:
    text = feedback["text"]
    vec = embed.query(text)
    similar = lessons.similar_approved(session, run["project_id"], vec)
    decisions = context.search_decisions(session, run["project_id"], vec, limit=5)
    keyed = {f"L{i}": l for i, l in enumerate(similar, 1)} | {f"D{i}": d for i, d in enumerate(decisions, 1)}
    existing = "\n".join(f"[{k}] {v['text']}" for k, v in keyed.items()) or "(none)"
    user = (f"Feature: {run['intent']['feature']}\nFeedback: {text}\n\n"
            f"Existing approved lessons and current decisions:\n{existing}")
    out, _ = llm.parse(SYSTEM, user, Proposal, effort="low", max_tokens=4000)
    if not out.reusable or not out.lesson.strip():
        return {"proposed": None, "reason": "feedback was a one-off fix with no reusable guidance"}

    dup_id = keyed[out.duplicate_of]["_id"] if out.duplicate_of in keyed else None
    if not dup_id and similar and similar[0]["score"] >= config.DUPLICATE_SCORE:
        dup_id = similar[0]["_id"]
    conflicts = [{"key": k, "type": "lesson" if k.startswith("L") else "decision", "id": keyed[k]["_id"],
                  "text": keyed[k]["text"]} for k in out.conflicts if k in keyed]
    lesson = lessons.propose(session, run["project_id"], out.lesson.strip(), run["_id"], feedback["_id"],
                             out.task_tags, dup_id, conflicts)
    return {"proposed": lesson}
