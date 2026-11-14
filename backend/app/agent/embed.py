"""Voyage AI embeddings and reranking. Documents and queries use different input_type values."""
import voyageai
from langsmith import traceable

from app import config

_client = None


def _c():
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=config.VOYAGE_API_KEY or None, timeout=20, max_retries=1)
    return _client


def documents(texts: list[str]) -> list[list[float]]:
    out = []
    for i in range(0, len(texts), 64):
        out += _c().embed(texts[i:i + 64], model=config.EMBED_MODEL, input_type="document").embeddings
    return out


def document(text: str) -> list[float]:
    return documents([text])[0]


@traceable(run_type="embedding", name="voyage.embed_query", process_inputs=lambda _: {}, process_outputs=lambda _: {})
def query(text: str) -> list[float]:
    return _c().embed([text], model=config.EMBED_MODEL, input_type="query").embeddings[0]


@traceable(run_type="retriever", name="voyage.rerank", process_inputs=lambda _: {}, process_outputs=lambda _: {})
def rerank(query_text: str, docs: list[str], top_k: int) -> list[tuple[int, float]]:
    """Return [(index into docs, relevance score)] best first."""
    if not docs:
        return []
    res = _c().rerank(query_text, docs, model=config.RERANK_MODEL, top_k=min(top_k, len(docs)))
    return [(r.index, r.relevance_score) for r in res.results]
