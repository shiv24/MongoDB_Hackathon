"""Short-lived tokens that let ElevenLabs agent tool calls act as the logged-in user.

The browser receives the raw token once and passes it to the agent as the secret dynamic variable
`secret__pf_token` (never sent to the LLM). Tool webhooks send it back in a header. Only a SHA-256
hash is stored; a TTL index removes expired rows.
"""
import hashlib
import secrets
from datetime import timedelta

from app import config
from app.db import get_db, new_id, now
from app.errors import NotLoggedIn


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def mint(session: dict, project_id: str) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    sid = new_id()
    get_db().agent_sessions.insert_one({
        "_id": sid, "token_hash": _hash(token), "project_id": project_id, "session": session,
        "current_run_id": None, "created_at": now(),
        "expires_at": now() + timedelta(hours=config.AGENT_SESSION_HOURS),
    })
    return sid, token


def resolve(token: str | None) -> dict:
    """Return the agent-session row (with the user's session) for a token, or raise."""
    if not token:
        raise NotLoggedIn("missing agent session token")
    row = get_db().agent_sessions.find_one({"token_hash": _hash(token)})
    if not row or row["expires_at"] < now():
        raise NotLoggedIn("agent session expired; start a new conversation")
    return row


def set_run(agent_session_id: str, run_id: str) -> None:
    get_db().agent_sessions.update_one({"_id": agent_session_id}, {"$set": {"current_run_id": run_id}})


def get_for_user(session: dict, agent_session_id: str) -> dict:
    row = get_db().agent_sessions.find_one({"_id": agent_session_id})
    if not row or row["session"]["user_id"] != session["user_id"]:
        raise NotLoggedIn("unknown agent session")
    return row
