import sys
from pathlib import Path

import mongomock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db as db_mod  # noqa: E402
from app.agent import embed  # noqa: E402

ALICE = {"user_id": "alice", "team_id": "team_a", "project_ids": ["signup", "billing"], "role": "publisher", "name": "Alice"}
BOB = {"user_id": "bob", "team_id": "team_a", "project_ids": ["signup"], "role": "member", "name": "Bob"}
CAROL = {"user_id": "carol", "team_id": "team_b", "project_ids": ["orbit"], "role": "admin", "name": "Carol"}


@pytest.fixture
def db(monkeypatch):
    """In-memory Mongo + fake embeddings. $vectorSearch is NOT available here; those paths are
    covered by the Atlas integration test."""
    mdb = mongomock.MongoClient(tz_aware=True).db
    db_mod.set_db(mdb)
    fake = lambda t: [float(len(t) % 7), 1.0, 0.5]  # noqa: E731
    monkeypatch.setattr(embed, "document", fake)
    monkeypatch.setattr(embed, "query", fake)
    monkeypatch.setattr(embed, "documents", lambda ts: [fake(t) for t in ts])
    yield mdb
    db_mod.set_db(None)
