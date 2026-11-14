"""Access scopes, derived from the session only. Every read of lessons/decisions/sources uses these.

Session shape (set by /login): {"user_id", "team_id", "project_ids": [...], "role"}.
"""


class ScopeError(PermissionError):
    """Caller asked for a project they are not a member of."""


def require_project(session: dict, project_id: str) -> None:
    if project_id not in session.get("project_ids", []):
        raise ScopeError(f"user {session.get('user_id')} is not a member of project {project_id}")


def lesson_filter(session: dict, project_id: str, status: str = "approved") -> dict:
    """$vectorSearch pre-filter: approved lessons this user may see for this project.

    team lessons of the caller's team, project lessons of this project, and the caller's own
    personal lessons. Uses only operators $vectorSearch filters support ($and/$or/$eq).
    """
    require_project(session, project_id)
    return {
        "$and": [
            {"team_id": {"$eq": session["team_id"]}},
            {"status": {"$eq": status}},
            {
                "$or": [
                    {"scope": {"$eq": "team"}},
                    {"$and": [{"scope": {"$eq": "project"}}, {"project_id": {"$eq": project_id}}]},
                    {"$and": [{"scope": {"$eq": "personal"}}, {"owner_id": {"$eq": session["user_id"]}}]},
                ]
            },
        ]
    }


def project_filter(session: dict, project_id: str) -> dict:
    """Pre-filter for sources and decisions: same team, this project only."""
    require_project(session, project_id)
    return {"$and": [{"team_id": {"$eq": session["team_id"]}}, {"project_id": {"$eq": project_id}}]}
