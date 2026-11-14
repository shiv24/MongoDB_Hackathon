"""The ONLY module that reads or writes `lessons`. Every query goes through repo.scope."""


def search(session: dict, project_id: str, query_embedding: list[float], limit: int = 8) -> list[dict]:
    # TODO: expire_due(session["team_id"]) first, then $vectorSearch with scope.lesson_filter(...)
    raise NotImplementedError


def propose(session: dict, project_id: str, text: str, evidence_run_id: str, feedback_id: str) -> dict:
    # TODO: status="proposed"; check duplicates/conflicts vs approved lessons; log event "proposed"
    raise NotImplementedError


def approve(session: dict, lesson_id: str, scope: str, text: str | None = None) -> dict:
    # TODO: check caller may publish at `scope` (team scope needs team permission); log "approved"
    raise NotImplementedError


def reject(session: dict, lesson_id: str) -> None:
    raise NotImplementedError


def correct(session: dict, lesson_id: str, new_text: str) -> dict:
    # TODO: new revision with supersedes=lesson_id; old -> "superseded"; log "corrected"
    raise NotImplementedError


def retire(session: dict, lesson_id: str) -> None:
    raise NotImplementedError


def forget(session: dict, lesson_id: str) -> None:
    # TODO: remove from future use; mark briefs that cited it stale; log "forgotten" WITHOUT text
    raise NotImplementedError


def expire_due(team_id: str) -> list[str]:
    """Mark approved lessons past expires_at as "expired" and log each (cause "ttl").

    Reads also filter on status, so expired lessons are excluded immediately. The TTL index on
    purge_at deletes them later; TTL alone is insufficient because it runs in the background.
    """
    raise NotImplementedError


def current_revisions(session: dict, lesson_ids: list[str]) -> dict[str, dict]:
    """Pre-execution recheck: current status, scope and revision for each cited lesson."""
    raise NotImplementedError
