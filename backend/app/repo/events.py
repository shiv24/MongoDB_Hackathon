"""Append-only writer for memory_events. Never update or delete here.

Events explain approvals, corrections, scope changes, retirement, expiry and forgetting.
A "forgotten" event must not contain the forgotten text.
"""


def log_event(record_type, record_id, team_id, event, actor, cause, before=None, after=None) -> None:
    raise NotImplementedError
