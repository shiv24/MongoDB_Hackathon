"""Live Atlas checks against the seeded fixtures (python scripts/seed.py --reset).

Skipped unless MONGODB_URI and VOYAGE_API_KEY are set. Uses real $vectorSearch.
"""
import pytest

from app import config

pytestmark = pytest.mark.skipif(not (config.MONGODB_URI and config.VOYAGE_API_KEY),
                                reason="needs MONGODB_URI + VOYAGE_API_KEY and seeded fixtures")

ALICE = {"user_id": "alice", "team_id": "team_a", "project_ids": ["lumen-signup", "lumen-billing"], "role": "admin"}
BOB = {"user_id": "bob", "team_id": "team_a", "project_ids": ["lumen-signup"], "role": "member"}
CAROL = {"user_id": "carol", "team_id": "team_b", "project_ids": ["orbit-signup"], "role": "admin"}


@pytest.fixture(scope="module")
def live():
    from app import db as db_mod
    from app.agent import embed
    db_mod.set_db(None)
    database = db_mod.get_db()
    if not database.users.find_one({"_id": "alice"}):
        pytest.skip("fixtures not seeded")
    return database, embed.query("build the signup page with button labels and password rules")


def test_team_b_retrieves_zero_team_a_memory(live):
    from app.repo import context, lessons
    _, vec = live
    for hits in (lessons.search(CAROL, "orbit-signup", vec), context.search_decisions(CAROL, "orbit-signup", vec),
                 context.search_sources(CAROL, "orbit-signup", vec)):
        assert hits and all(h["team_id"] == "team_b" for h in hits)


def test_only_current_authorized_memory_is_retrieved(live):
    from app.repo import context, lessons
    _, vec = live
    alice_ids = {h["_id"] for h in lessons.search(ALICE, "lumen-signup", vec)}
    bob_ids = {h["_id"] for h in lessons.search(BOB, "lumen-signup", vec)}
    assert "les-a-pwhint" in alice_ids and "les-a-teamtone" in alice_ids
    assert "les-a-singlecol" in alice_ids and "les-a-singlecol" not in bob_ids   # personal
    for excluded in ("les-a-darkmode", "les-a-stale", "les-a-twocol", "les-b-caps"):  # proposed/expired/retired/other team
        assert excluded not in alice_ids | bob_ids
    dec_ids = {d["_id"] for d in context.search_decisions(ALICE, "lumen-signup", vec)}
    assert "dec-a-phone-r2" in dec_ids and "dec-a-phone-r1" not in dec_ids     # superseded


def test_non_member_project_rejected(live):
    from app.repo import lessons
    from app.repo.scope import ScopeError
    _, vec = live
    with pytest.raises(ScopeError):
        lessons.search(BOB, "lumen-billing", vec)
