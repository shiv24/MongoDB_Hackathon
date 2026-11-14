"""Before a brief leaves PromptForge (export), recheck every cited memory against the authoritative records."""
from app.agent import brief as brief_mod
from app.repo import context, lessons


def recheck(session: dict, run: dict) -> list[dict]:
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
