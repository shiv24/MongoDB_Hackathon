import pytest

from app.agent import brief

ENTRIES = [{"key": "S1", "type": "source", "id": "s", "revision": 2, "title": "Spec", "text": "fields"},
           {"key": "D1", "type": "decision", "id": "d", "revision": 1, "owner_id": "alice", "text": "Use Lumen ID"},
           {"key": "L1", "type": "lesson", "id": "l", "revision": 1, "scope": "project", "text": "Mobile layout"}]


def _agent_payload():
    return {"objective": "Build signup",
            "requirements": ["Collect work email [S1] [S9]", "Be nice"],
            "current_decisions": ["Use Lumen ID for account creation [D1]"],
            "preferences": ["Include a mobile layout [L1]"],
            "acceptance_checks": ["The form has an email field [S1]"],
            "blocking_questions": ["What are the company size values? [S1]"],
            "other_questions": ["Should we show a logo?"],
            "assumptions": ["Desktop first"]}


def test_from_agent_parses_citations_and_questions():
    b = brief.validate_citations(brief.from_agent(_agent_payload()), ENTRIES)
    assert b["requirements"][0] == {"text": "Collect work email", "sources": ["S1"], "uncited": False}
    assert b["requirements"][1]["uncited"] is True
    assert b["citation_warnings"] == ["S9"]
    assert [q["blocking"] for q in b["open_questions"]] == [True, False]
    assert brief.cited_keys(b) == {"S1", "D1", "L1"}


def test_from_agent_requires_objective():
    with pytest.raises(ValueError):
        brief.from_agent({"objective": " "})


def test_resolved_questions():
    assert brief.parse_resolved(["Company size? => 1-10, 11-50, 51+", "junk"]) == [
        {"question": "Company size?", "answer": "1-10, 11-50, 51+"}]


def test_markdown_export_has_citations_and_provenance():
    run = {"request": "build signup", "intent": {"feature": "Signup page"},
           "brief": brief.validate_citations(brief.from_agent(_agent_payload()), ENTRIES), "provenance": ENTRIES,
           "answers": [{"question": "Q?", "answer": "A."}]}
    md = brief.to_markdown(run)
    assert "- Collect work email [S1]" in md and "*(uncited)*" in md and "**Blocking**" in md
    assert "[D1] team decision `d` revision 1" in md and "## Resolved questions" in md
