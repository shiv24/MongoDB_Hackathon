"""Step 1: resolve the document and feature from the request.

If two documents or features fit and the request doesn't distinguish them, return ONE focused
clarifying question instead of guessing.
"""
from pydantic import BaseModel, Field

from app.agent import llm


class Intent(BaseModel):
    feature: str = Field(description="The concrete thing the user wants built or changed, in one sentence")
    documents: list[str] = Field(description="Titles of the project sources the request refers to (exact titles from the list)")
    clarifying_question: str | None = Field(description="One focused question if the request is genuinely ambiguous between documents or features; otherwise null")
    search_query: str = Field(description="A self-contained retrieval query: feature plus key nouns from the request")


SYSTEM = """You resolve what a teammate is asking an AI to build, inside one project.
You are given the project's source titles, its current team decisions, and the request (possibly a speech transcript).
Resolve references like "that doc" or "the signup page" to specific source titles and a specific feature.
Ask a clarifying question ONLY when two or more documents or features plausibly fit and choosing wrong would change the work. Ask exactly one short question. If a clarification answer is provided, use it and do not ask again.
Never invent document titles; use only titles from the list."""


def resolve(project: dict, source_titles: list[str], decisions: list[str], request: str,
            clarification: str | None = None) -> tuple[Intent, str]:
    user = (f"Project: {project['name']}\n"
            f"Sources:\n" + "\n".join(f"- {t}" for t in source_titles or ["(none)"]) + "\n"
            f"Current decisions:\n" + "\n".join(f"- {d}" for d in decisions or ["(none)"]) + "\n\n"
            f"Request: {request}\n")
    if clarification:
        user += f"Clarification from the user: {clarification}\n"
    intent, model = llm.parse(SYSTEM, user, Intent, effort="low", max_tokens=4000)
    if clarification:
        intent.clarifying_question = None
    return intent, model
