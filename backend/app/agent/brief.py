"""Step 3: assemble the cited brief.

Sections: objective, requirements, current_decisions, implementation_context, preferences,
acceptance_checks, open_questions, provenance. Every instruction cites a source or memory revision.
A preference never silently overrides a requirement; unresolved conflicts go to open_questions.
Never invent files or interfaces - flag them as unknown.
"""


def to_markdown(brief: dict) -> str:
    """Export format for coding tools."""
    raise NotImplementedError
