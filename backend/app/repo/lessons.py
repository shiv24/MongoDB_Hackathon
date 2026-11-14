"""The ONLY module allowed to query `lessons`. Every query is scoped to team_id."""


def get_lessons(team_id: str, query_embedding: list[float] | None = None,
                status: str | list[str] = "active", limit: int = 8) -> list[dict]:
    # TODO(P2): $vectorSearch with filter {team_id, status} as a pre-filter
    raise NotImplementedError
