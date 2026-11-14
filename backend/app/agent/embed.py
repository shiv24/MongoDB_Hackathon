"""Voyage AI embeddings. Documents and queries use different input_type values."""
import voyageai

from app import config

_client = None


def _c():
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=config.VOYAGE_API_KEY or None)
    return _client


def documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    out = []
    for i in range(0, len(texts), 64):
        out += _c().embed(texts[i:i + 64], model=config.EMBED_MODEL, input_type="document").embeddings
    return out


def document(text: str) -> list[float]:
    return documents([text])[0]


def query(text: str) -> list[float]:
    return _c().embed([text], model=config.EMBED_MODEL, input_type="query").embeddings[0]
