"""Runs: request, brief, cited context revisions, model, artifact, check results. Plus feedback."""


def create(session: dict, project_id: str, request_text: str, brief: dict, provenance: list[dict]) -> dict:
    raise NotImplementedError


def get(session: dict, run_id: str) -> dict:
    # TODO: only runs in the caller's team and projects
    raise NotImplementedError


def add_feedback(session: dict, run_id: str, text: str) -> dict:
    raise NotImplementedError
