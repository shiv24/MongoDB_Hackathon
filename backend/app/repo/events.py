"""Append-only writer for memory_events. Never update or delete here."""


def log_event(lesson_id, team_id, event, actor, cause, before=None, after=None) -> None:
    # TODO(P2): insert_one with at=now
    raise NotImplementedError
