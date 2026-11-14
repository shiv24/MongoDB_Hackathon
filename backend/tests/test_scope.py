import pytest

from app.repo.scope import ScopeError, lesson_filter, project_filter, source_filter

ALICE = {"user_id": "alice", "team_id": "team_a", "project_ids": ["signup"], "role": "member"}


def _flatten(f):
    """All {field: {"$eq": value}} leaves in a filter."""
    if isinstance(f, dict):
        for k, v in f.items():
            if k in ("$and", "$or"):
                for sub in v:
                    yield from _flatten(sub)
            else:
                yield k, v["$eq"]


def test_lesson_filter_pins_team_and_approved():
    leaves = list(_flatten(lesson_filter(ALICE, "signup")))
    assert ("team_id", "team_a") in leaves
    assert ("status", "approved") in leaves
    assert ("owner_id", "alice") in leaves
    assert ("project_id", "signup") in leaves


def test_lesson_filter_top_level_is_and():
    f = lesson_filter(ALICE, "signup")
    assert set(f) == {"$and"}
    assert {"team_id": {"$eq": "team_a"}} in f["$and"]


def test_non_member_project_is_rejected():
    with pytest.raises(ScopeError):
        lesson_filter(ALICE, "billing")
    with pytest.raises(ScopeError):
        project_filter(ALICE, "billing")
    with pytest.raises(ScopeError):
        source_filter(ALICE, "billing")


def test_source_filter_pins_team_and_scope():
    f = source_filter(ALICE, "signup")
    assert {"team_id": {"$eq": "team_a"}} in f["$and"]
    branches = f["$and"][1]["$or"]
    assert {"scope": {"$eq": "team"}} in branches
    assert {"$and": [{"scope": {"$eq": "project"}}, {"project_id": {"$eq": "signup"}}]} in branches
    assert {"$and": [{"scope": {"$eq": "personal"}}, {"owner_id": {"$eq": "alice"}}]} in branches
