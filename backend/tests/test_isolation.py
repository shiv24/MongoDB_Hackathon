import pytest


@pytest.mark.skip(reason="TODO: needs Atlas fixtures - seed team_a + team_b, assert team_b search returns zero team_a ids")
def test_team_b_cannot_retrieve_team_a_memory():
    ...
