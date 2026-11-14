"""Step 2: authorized retrieval. Embed the query once, then search source chunks, current decisions
and approved lessons through repo/ (scope pre-filters are applied before semantic search)."""
from app.agent import embed
from app.repo import context, lessons


def gather(session: dict, project_id: str, query: str) -> list[dict]:
    """Return provenance entries keyed S1.., D1.., L1.. for the brief to cite."""
    vec = embed.query(query)
    entries = []
    for i, s in enumerate(context.search_sources(session, project_id, vec), 1):
        entries.append({"key": f"S{i}", "type": "source", "id": s["source_id"], "chunk_id": s["_id"],
                        "revision": s["revision"], "title": s["title"], "text": s["text"],
                        "score": round(s["score"], 4)})
    for i, d in enumerate(context.search_decisions(session, project_id, vec), 1):
        entries.append({"key": f"D{i}", "type": "decision", "id": d["_id"], "revision": d["revision"],
                        "owner_id": d["owner_id"], "text": d["text"], "score": round(d["score"], 4)})
    for i, l in enumerate(lessons.search(session, project_id, vec), 1):
        entries.append({"key": f"L{i}", "type": "lesson", "id": l["_id"], "revision": l["revision"],
                        "scope": l["scope"], "owner_id": l["owner_id"], "approved_by": l.get("approved_by"),
                        "text": l["text"], "score": round(l["score"], 4)})
    return entries
