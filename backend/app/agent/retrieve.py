"""Step 2: authorized retrieval. Embed the query once (Voyage), run scoped $vectorSearch over source
chunks, current decisions and approved lessons, then rerank source chunks with Voyage rerank."""
from langsmith import traceable

from app import config
from app.agent import embed
from app.repo import context, lessons


@traceable(run_type="retriever", name="promptforge.gather_context", process_inputs=lambda _: {}, process_outputs=lambda _: {})
def gather(session: dict, project_id: str, query: str) -> list[dict]:
    """Return provenance entries keyed S1.., D1.., L1.. for the brief to cite."""
    vec = embed.query(query)
    chunks = context.search_sources(session, project_id, vec, limit=config.RETRIEVE_LIMIT * 2)
    order = embed.rerank(query, [f"{c['title']}\n{c['text']}" for c in chunks], config.RETRIEVE_LIMIT)
    entries = []
    for i, (idx, rel) in enumerate(order, 1):
        s = chunks[idx]
        entries.append({"key": f"S{i}", "type": "source", "id": s["source_id"], "chunk_id": s["_id"],
                        "revision": s["revision"], "title": s["title"], "text": s["text"],
                        "score": round(s["score"], 4), "rerank": round(rel, 4)})
    for i, d in enumerate(context.search_decisions(session, project_id, vec), 1):
        entries.append({"key": f"D{i}", "type": "decision", "id": d["_id"], "revision": d["revision"],
                        "owner_id": d["owner_id"], "text": d["text"], "score": round(d["score"], 4)})
    candidates = lessons.search(session, project_id, vec)
    ranked = embed.rerank(query, [l['text'] for l in candidates], config.RETRIEVE_LIMIT)
    relevant_lessons = [candidates[idx] for idx, relevance in ranked
                        if relevance >= config.LESSON_RELEVANCE_MIN]
    for i, l in enumerate(relevant_lessons, 1):
        entries.append({"key": f"L{i}", "type": "lesson", "id": l["_id"], "revision": l["revision"],
                        "scope": l["scope"], "owner_id": l["owner_id"], "approved_by": l.get("approved_by"),
                        "text": l["text"], "score": round(l["score"], 4)})
    return entries
