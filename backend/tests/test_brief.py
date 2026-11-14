from app.agent import brief, execute

ENTRIES = [{"key": "S1", "type": "source", "id": "s", "revision": 2, "title": "Spec", "text": "fields"},
           {"key": "D1", "type": "decision", "id": "d", "revision": 1, "owner_id": "alice", "text": "Use Lumen ID"},
           {"key": "L1", "type": "lesson", "id": "l", "revision": 1, "scope": "project", "text": "Mobile layout"}]


def _brief():
    return {"objective": "Build signup",
            "requirements": [{"text": "Collect email", "sources": ["S1", "S9"]}, {"text": "Be nice", "sources": []}],
            "current_decisions": [{"text": "Lumen ID", "sources": ["D1"]}], "implementation_context": [],
            "preferences": [{"text": "Mobile layout", "sources": ["L1"]}],
            "acceptance_checks": [{"text": "Has mobile layout", "sources": ["L1"]}],
            "open_questions": [{"text": "Company size values?", "blocking": True, "sources": ["S1"]}],
            "assumptions": []}


def test_unknown_citations_dropped_and_uncited_flagged():
    b = brief.validate_citations(_brief(), ENTRIES)
    assert b["requirements"][0]["sources"] == ["S1"] and b["citation_warnings"] == ["S9"]
    assert b["requirements"][1]["uncited"] is True
    assert brief.cited_keys(b) == {"S1", "D1", "L1"}


def test_markdown_export_has_citations_and_provenance():
    run = {"request": "build signup", "intent": {"feature": "Signup page"},
           "brief": brief.validate_citations(_brief(), ENTRIES), "provenance": ENTRIES,
           "answers": [{"question": "Q?", "answer": "A."}]}
    md = brief.to_markdown(run)
    assert "- Collect email [S1]" in md and "*(uncited)*" in md and "**Blocking**" in md
    assert "[D1] team decision `d` revision 1" in md and "## Resolved questions" in md


def test_sanitize_strips_scripts_and_handlers():
    html, notes = execute.sanitize('<html><body onload="x()"><script>alert(1)</script><a href="javascript:x">a</a></body></html>')
    assert "<script" not in html and "onload" not in html and "javascript:" not in html
    assert len(notes) == 2


def test_extract_html_from_fenced_output():
    assert execute.extract_html("Here:\n```html\n<!doctype html><html></html>\n```").startswith("<!doctype html>")
