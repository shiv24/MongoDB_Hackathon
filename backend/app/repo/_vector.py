from app import config


def vector_search(coll, index: str, embedding: list[float], filter: dict, limit: int) -> list[dict]:
    """$vectorSearch with the scope filter as a PRE-filter (applied before similarity scoring)."""
    pipeline = [
        {"$vectorSearch": {"index": index, "path": "embedding", "queryVector": embedding,
                           "numCandidates": max(config.NUM_CANDIDATES, limit * 10),
                           "limit": limit, "filter": filter}},
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$project": {"embedding": 0}},
    ]
    return list(coll.aggregate(pipeline))
