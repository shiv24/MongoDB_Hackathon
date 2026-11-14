"""Step 5: recheck cited memory, then run the brief with the configured model.

The artifact type for this prototype is a single self-contained HTML page.
"""
import re

from bs4 import BeautifulSoup

from app.agent import brief as brief_mod
from app.agent import llm
from app.repo import context, lessons

SYSTEM = """You implement a brief as ONE self-contained HTML document.
- Satisfy every requirement, decision and acceptance check in the brief. Preferences apply unless they conflict with a requirement.
- Inline all CSS in a <style> tag. No JavaScript, no <script> tags, no external fonts, images or URLs. Use CSS shapes or inline SVG for visuals.
- Include <meta name="viewport" content="width=device-width, initial-scale=1">.
- Where the brief leaves something unresolved, choose the simplest reasonable option and add an HTML comment noting the assumption.
Return only the HTML document, starting with <!doctype html>."""


def recheck(session: dict, run: dict) -> list[dict]:
    """Compare every cited decision, lesson and source against the authoritative records now."""
    changes = []
    cited = brief_mod.cited_keys(run["brief"])
    for e in run.get("provenance", []):
        if e["key"] not in cited:
            continue
        if e["type"] == "lesson":
            cur = lessons.current_state(session, e["id"])
            if cur is None:
                changes.append({"key": e["key"], "type": "lesson", "id": e["id"], "change": "removed or no longer visible"})
            elif cur["status"] != "approved":
                changes.append({"key": e["key"], "type": "lesson", "id": e["id"], "change": f"now {cur['status']}",
                                "replacement": cur.get("superseded_by")})
        elif e["type"] == "decision":
            try:
                cur = context.get_decision(session, e["id"])
            except LookupError:
                cur = None
            if cur is None:
                changes.append({"key": e["key"], "type": "decision", "id": e["id"], "change": "removed"})
            elif cur["status"] != "current":
                changes.append({"key": e["key"], "type": "decision", "id": e["id"], "change": "superseded",
                                "replacement": cur.get("superseded_by")})
        elif e["type"] == "source":
            latest = context.latest_source_revision(session["team_id"], e["id"])
            if latest != e["revision"]:
                changes.append({"key": e["key"], "type": "source", "id": e["id"],
                                "change": f"revision {e['revision']} -> {latest}"})
    return changes


def generate(run: dict) -> tuple[str, str, list[str]]:
    """Return (sanitized html, model that served it, sanitizer notes)."""
    text, model = llm.generate_text(SYSTEM, brief_mod.to_markdown(run))
    html = extract_html(text)
    html, notes = sanitize(html)
    return html, model, notes


def extract_html(text: str) -> str:
    m = re.search(r"```(?:html)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = text.lower().find("<!doctype")
    if start < 0:
        start = text.lower().find("<html")
    return text[start:].strip() if start >= 0 else text.strip()


def sanitize(html: str) -> tuple[str, list[str]]:
    """Defence in depth (the iframe is also sandboxed): strip scripts, event handlers, javascript: URLs."""
    soup = BeautifulSoup(html, "html.parser")
    notes = []
    scripts = soup.find_all(["script", "iframe", "object", "embed"])
    if scripts:
        notes.append(f"removed {len(scripts)} script/embed element(s)")
        for s in scripts:
            s.decompose()
    handlers = 0
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            val = tag.attrs[attr]
            if attr.lower().startswith("on") or (isinstance(val, str) and val.strip().lower().startswith("javascript:")):
                del tag.attrs[attr]
                handlers += 1
    if handlers:
        notes.append(f"removed {handlers} event-handler/javascript attribute(s)")
    return str(soup), notes
