"""Step 3: the cited brief. The ElevenLabs agent writes it (via the save_brief tool); this module
normalizes, validates citations, and renders Markdown for export to a coding tool (e.g. Claude Code)."""
import re

CITE = re.compile(r"\[([SDLU]\d+)\]")
SECTIONS = ("requirements", "current_decisions", "implementation_context", "preferences", "acceptance_checks")


def context_block(entries: list[dict]) -> str:
    """Context as the agent sees it: one keyed entry per source chunk, decision, or lesson."""
    lines = []
    for e in entries:
        if e["type"] == "source":
            lines.append(f"[{e['key']}] source \"{e['title']}\" rev {e['revision']}:\n{e['text']}")
        elif e["type"] == "decision":
            lines.append(f"[{e['key']}] team decision rev {e['revision']} (owner {e['owner_id']}): {e['text']}")
        else:
            lines.append(f"[{e['key']}] approved {e['scope']} preference rev {e['revision']}: {e['text']}")
    return "\n\n".join(lines) or "(no context found)"


def _item(text: str) -> dict:
    keys = list(dict.fromkeys(CITE.findall(text)))
    clean = re.sub(r"\s*\[[SDLU]\d+\]", "", text).strip()
    return {"text": clean, "sources": keys}


def from_agent(payload: dict) -> dict:
    """Agent tool input (lists of strings with [S1]-style citations) -> brief dict."""
    brief = {"objective": (payload.get("objective") or "").strip()}
    for section in SECTIONS:
        brief[section] = [_item(t) for t in payload.get(section) or [] if t and t.strip()]
    brief["open_questions"] = (
        [{**_item(t), "blocking": True} for t in payload.get("blocking_questions") or [] if t and t.strip()]
        + [{**_item(t), "blocking": False} for t in payload.get("other_questions") or [] if t and t.strip()])
    brief["assumptions"] = [t.strip() for t in payload.get("assumptions") or [] if t and t.strip()]
    if not brief["objective"]:
        raise ValueError("brief needs an objective")
    return brief


def parse_resolved(lines: list[str]) -> list[dict]:
    out = []
    for line in lines or []:
        q, _, a = line.partition("=>")
        if q.strip() and a.strip():
            out.append({"question": q.strip(), "answer": a.strip()})
    return out


def validate_citations(brief: dict, entries: list[dict]) -> dict:
    """Drop citation keys that don't exist; flag items left without any citation."""
    if not isinstance(brief.get("objective"), str) or not brief["objective"].strip():
        raise ValueError("Brief needs an objective")
    valid = {e["key"] for e in entries}
    unknown = set()
    for section in ("requirements", "current_decisions", "implementation_context", "preferences",
                    "acceptance_checks", "open_questions"):
        if not isinstance(brief.get(section, []), list):
            raise ValueError("Brief sections must be lists")
        for item in brief.get(section, []):
            if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not isinstance(item.get("sources", []), list):
                raise ValueError("Invalid brief item")
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
                 "lesson": f"{e.get('scope')} lesson", "user": "user request"}[e["type"]]
        out.append(f"- [{k}] {label} `{e['id']}` revision {e['revision']}: {e['text'][:200]}")
    return "\n".join(out) + "\n"
