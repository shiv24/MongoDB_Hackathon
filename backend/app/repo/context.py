"""Sources (spec / repo snapshot chunks) and team decisions. Scoped by repo.scope.project_filter."""


def search_sources(session: dict, project_id: str, query_embedding: list[float], limit: int = 8) -> list[dict]:
    raise NotImplementedError


def search_decisions(session: dict, project_id: str, query_embedding: list[float], limit: int = 8) -> list[dict]:
    # TODO: status="current" only; superseded decisions never reach a brief
    raise NotImplementedError


def add_source(session: dict, project_id: str, title: str, text: str, revision: str) -> dict:
    # TODO: chunk + embed; store source_id, revision, chunk index
    raise NotImplementedError


def add_decision(session: dict, project_id: str, text: str) -> dict:
    # TODO: owner = session user; must be authorized for the project; log "decision_created"
    raise NotImplementedError


def supersede_decision(session: dict, decision_id: str, new_text: str) -> dict:
    # TODO: new revision with supersedes=decision_id; old -> "superseded"; log event
    raise NotImplementedError
