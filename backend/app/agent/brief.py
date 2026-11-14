"""Step 3: assemble the cited brief, and render it as Markdown for export."""
from pydantic import BaseModel, Field

from app.agent import llm


class Cited(BaseModel):
    text: str
    sources: list[str] = Field(description="Citation keys such as S1, D2, L1 that support this item")


class Question(BaseModel):
    text: str
    blocking: bool = Field(description="True if the work cannot be done correctly without an answer")
    sources: list[str]


class BriefOut(BaseModel):
    objective: str
    requirements: list[Cited]
    current_decisions: list[Cited]
    implementation_context: list[Cited]
    preferences: list[Cited]
    acceptance_checks: list[Cited] = Field(description="Concrete, checkable statements about the result")
    open_questions: list[Question]
    assumptions: list[str]


SYSTEM = """You assemble a brief that another AI model or coding tool will execute. The brief must be self-contained.
Rules:
- Every requirement, decision, implementation note and preference cites the context keys it comes from (S = source chunk, D = team decision, L = approved lesson). Use only keys you were given.
- Requirements come from sources. Keep EVERY applicable requirement, even if the brief gets longer.
- Decisions are authoritative. A preference (L) never overrides a requirement or a decision. A request phrase never silently supersedes a decision.
- If sources/decisions conflict, or a needed fact is missing (e.g. a required field is undefined), add an open question instead of guessing. Mark it blocking if the work would likely be wrong without the answer.
- Never invent files, interfaces, or services that are not in the context; if one seems needed, ask an open question.
- Acceptance checks are concrete and verifiable by inspecting the result (e.g. "the page has a mobile layout below 600px width").
- Assumptions list anything you assumed that the user should confirm. Keep each item to one or two sentences."""


def context_block(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        if e["type"] == "source":
            lines.append(f"[{e['key']}] source \"{e['title']}\" rev {e['revision']}:\n{e['text']}")
        elif e["type"] == "decision":
            lines.append(f"[{e['key']}] team decision rev {e['revision']} (owner {e['owner_id']}): {e['text']}")
        else:
            lines.append(f"[{e['key']}] approved {e['scope']} preference rev {e['revision']}: {e['text']}")
    return "\n\n".join(lines) or "(no context found)"


def assemble(request: str, intent: dict, entries: list[dict], answers: list[dict] | None = None) -> tuple[dict, str]:
    user = (f"Request: {request}\nResolved feature: {intent['feature']}\n"
            f"Referenced documents: {', '.join(intent.get('documents') or []) or '(none)'}\n\n"
            f"Context:\n{context_block(entries)}\n")
    if answers:
        user += "\nThe user already answered these questions; use the answers and do not ask them again:\n"
        user += "\n".join(f"- Q: {a['question']}\n  A: {a['answer']}" for a in answers)
    out, model = llm.parse(SYSTEM, user, BriefOut, effort="medium")
    return validate_citations(out.model_dump(), entries), model


def validate_citations(brief: dict, entries: list[dict]) -> dict:
    """Drop citation keys that don't exist; flag items left without any citation."""
    valid = {e["key"] for e in entries}
    unknown = set()
    for section in ("requirements", "current_decisions", "implementation_context", "preferences",
                    "acceptance_checks", "open_questions"):
        for item in brief.get(section, []):
            bad = [k for k in item.get("sources", []) if k not in valid]
            unknown.update(bad)
            item["sources"] = [k for k in item.get("sources", []) if k in valid]
            if section not in ("acceptance_checks", "open_questions"):
                item["uncited"] = not item["sources"]
    brief["citation_warnings"] = sorted(unknown)
    return brief


def cited_keys(brief: dict) -> set[str]:
    keys = set()
    for section in ("requirements", "current_decisions", "implementation_context", "preferences",
                    "acceptance_checks", "open_questions"):
        for item in brief.get(section, []):
            keys.update(item.get("sources", []))
    return keys


def to_markdown(run: dict) -> str:
    b = run["brief"]
    prov = {e["key"]: e for e in run.get("provenance", [])}

    def cite(item):
        tag = " ".join(f"[{k}]" for k in item.get("sources", []))
        return f"- {item['text']} {tag}".rstrip() + (" *(uncited)*" if item.get("uncited") else "")

    out = [f"# Brief: {run['intent']['feature']}", "", f"**Request:** {run['request']}", "",
           "## Objective", b["objective"], ""]
    for title, key in (("Requirements", "requirements"), ("Current decisions", "current_decisions"),
                       ("Implementation context", "implementation_context"), ("Preferences", "preferences"),
                       ("Acceptance checks", "acceptance_checks")):
        out += [f"## {title}", *([cite(i) for i in b.get(key, [])] or ["- (none)"]), ""]
    qs = b.get("open_questions", [])
    out += ["## Open questions"]
    for q in qs:
        status = f"**Answered:** {q['answer']}" if q.get("answer") else ("**Blocking**" if q["blocking"] else "Non-blocking")
        out.append(f"- {q['text']} {' '.join(f'[{k}]' for k in q.get('sources', []))} - {status}")
    if not qs:
        out.append("- (none)")
    answered = ([run["clarification"]] if run.get("clarification") else []) + list(run.get("answers", []))
    if answered:
        out += ["", "## Resolved questions", *[f"- Q: {a['question']}\n  A: {a['answer']}" for a in answered]]
    out += ["", "## Assumptions", *([f"- {a}" for a in b.get("assumptions", [])] or ["- (none)"]), "",
            "## Provenance"]
    for k in sorted(cited_keys(b), key=lambda k: (k[0], int(k[1:]))):
        e = prov.get(k)
        if not e:
            continue
        label = {"source": f"source \"{e.get('title')}\"", "decision": "team decision",
                 "lesson": f"{e.get('scope')} lesson"}[e["type"]]
        out.append(f"- [{k}] {label} `{e['id']}` revision {e['revision']}: {e['text'][:200]}")
    return "\n".join(out) + "\n"
