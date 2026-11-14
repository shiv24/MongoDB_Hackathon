"""Sources (spec / repo snapshot chunks) and team decisions. Scoped by repo.scope.project_filter."""
from app import config
from app.agent import embed
from app.db import get_db, new_id, now
from app.errors import NotFound
from app.repo import events, scope
from app.repo._vector import vector_search


def chunk(text: str, size: int = config.CHUNK_CHARS) -> list[str]:
    """Split on blank lines, packing paragraphs up to `size` characters."""
    out, cur = [], ""
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        if cur and len(cur) + len(para) + 2 > size:
            out.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        out.append(cur)
    return out


# ---------- sources ----------

def add_source(session: dict, project_id: str, title: str, text: str, kind: str = "spec") -> dict:
    scope.require_project(session, project_id)
    db = get_db()
    existing = db.sources.find_one({"team_id": session["team_id"], "project_id": project_id, "title": title},
                                   sort=[("revision", -1)])
    source_id = existing["source_id"] if existing else new_id()
    revision = (existing["revision"] + 1) if existing else 1
    pieces = chunk(text)
    vectors = embed.documents([f"{title}\n\n{p}" for p in pieces])
    docs = [{"_id": new_id(), "team_id": session["team_id"], "project_id": project_id, "source_id": source_id,
             "title": title, "kind": kind, "revision": revision, "chunk_index": i, "text": p, "embedding": v,
             "added_by": session["user_id"], "created_at": now()} for i, (p, v) in enumerate(zip(pieces, vectors))]
    if docs:
        db.sources.insert_many(docs)
    return {"source_id": source_id, "title": title, "revision": revision, "chunks": len(docs)}


def latest_source_revision(team_id: str, source_id: str) -> int | None:
    d = get_db().sources.find_one({"team_id": team_id, "source_id": source_id}, sort=[("revision", -1)])
    return d["revision"] if d else None


def search_sources(session: dict, project_id: str, query_embedding: list[float],
                   limit: int = config.RETRIEVE_LIMIT) -> list[dict]:
    hits = vector_search(get_db().sources, "sources_vector", query_embedding,
                         scope.project_filter(session, project_id), limit * 2)
    # keep only chunks from each source's latest revision
    latest = {}
    for h in hits:
        latest.setdefault(h["source_id"], latest_source_revision(session["team_id"], h["source_id"]))
    return [h for h in hits if h["revision"] == latest[h["source_id"]]][:limit]


def list_sources(session: dict, project_id: str) -> list[dict]:
    pipeline = [
        {"$match": {"team_id": session["team_id"], "project_id": project_id}},
        {"$sort": {"revision": -1}},
        {"$group": {"_id": "$source_id", "title": {"$first": "$title"}, "kind": {"$first": "$kind"},
                    "revision": {"$first": "$revision"}, "added_by": {"$first": "$added_by"}}},
        {"$sort": {"title": 1}},
    ]
    scope.require_project(session, project_id)
    return [{"source_id": d["_id"], **{k: v for k, v in d.items() if k != "_id"}}
            for d in get_db().sources.aggregate(pipeline)]


# ---------- decisions ----------

def _decision_filter(session: dict, project_id: str) -> dict:
    f = scope.project_filter(session, project_id)
    f["$and"].append({"status": {"$eq": "current"}})
    return f


def add_decision(session: dict, project_id: str, text: str, cause: str = "user") -> dict:
    scope.require_project(session, project_id)
    doc = {"_id": new_id(), "team_id": session["team_id"], "project_id": project_id, "text": text,
           "owner_id": session["user_id"], "revision": 1, "supersedes": None, "status": "current",
           "embedding": embed.document(text), "created_at": now()}
    get_db().decisions.insert_one(doc)
    events.log_event("decision", doc["_id"], doc["team_id"], "created", session["user_id"], cause,
                     after={"text": text, "revision": 1})
    return _public(doc)


def get_decision(session: dict, decision_id: str) -> dict:
    d = get_db().decisions.find_one({"_id": decision_id, "team_id": session["team_id"]}, {"embedding": 0})
    if not d or d["project_id"] not in session["project_ids"]:
        raise NotFound(f"decision {decision_id} not found")
    return d


def supersede_decision(session: dict, decision_id: str, new_text: str) -> dict:
    old = get_decision(session, decision_id)
    if old["status"] != "current":
        raise ValueError("only the current revision of a decision can be corrected")
    db = get_db()
    new = {"_id": new_id(), "team_id": old["team_id"], "project_id": old["project_id"], "text": new_text,
           "owner_id": session["user_id"], "revision": old["revision"] + 1, "supersedes": old["_id"],
           "status": "current", "embedding": embed.document(new_text), "created_at": now()}
    db.decisions.insert_one(new)
    db.decisions.update_one({"_id": old["_id"]}, {"$set": {"status": "superseded", "superseded_by": new["_id"]}})
    events.log_event("decision", old["_id"], old["team_id"], "superseded", session["user_id"], "correction",
                     before={"text": old["text"], "revision": old["revision"]},
                     after={"superseded_by": new["_id"], "revision": new["revision"]})
    events.log_event("decision", new["_id"], new["team_id"], "created", session["user_id"], "correction",
                     after={"text": new_text, "revision": new["revision"], "supersedes": old["_id"]})
    return _public(new)


def search_decisions(session: dict, project_id: str, query_embedding: list[float],
                     limit: int = config.RETRIEVE_LIMIT) -> list[dict]:
    """Only status="current" decisions; superseded revisions never reach a brief."""
    hits = vector_search(get_db().decisions, "decisions_vector", query_embedding,
                         _decision_filter(session, project_id), limit)
    if not hits:
        return hits
    # the search index syncs asynchronously; confirm against the collection
    current = {d["_id"] for d in get_db().decisions.find(
        {"_id": {"$in": [h["_id"] for h in hits]}, "team_id": session["team_id"], "status": "current"}, {"_id": 1})}
    return [h for h in hits if h["_id"] in current]


def list_decisions(session: dict, project_id: str, include_superseded: bool = False) -> list[dict]:
    scope.require_project(session, project_id)
    q = {"team_id": session["team_id"], "project_id": project_id}
    if not include_superseded:
        q["status"] = "current"
    return list(get_db().decisions.find(q, {"embedding": 0}).sort("created_at", 1))


def _public(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "embedding"}
