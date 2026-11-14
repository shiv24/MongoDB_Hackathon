"""Turn the brief's acceptance checks into evidence. Every check is recorded with how it was checked;
failed and unrun checks stay visible."""
from typing import Literal

from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.agent import llm


class CheckResult(BaseModel):
    index: int
    result: Literal["passed", "failed", "not_run"]
    evidence: str


class Review(BaseModel):
    checks: list[CheckResult]


SYSTEM = """You review an HTML artifact against acceptance checks. For each check, decide passed or failed from the HTML/CSS itself, and quote or describe the specific evidence. Use not_run only if the check cannot be judged from static HTML/CSS (e.g. it needs a live backend). Be strict: if the evidence is absent, the check failed."""


def static_checks(html: str, sanitizer_notes: list[str]) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    viewport = soup.find("meta", attrs={"name": "viewport"})
    return [
        {"name": "Self-contained HTML document parses", "method": "static",
         "result": "passed" if soup.find("body") or soup.find("html") else "failed", "evidence": ""},
        {"name": "No scripts in generated output", "method": "static",
         "result": "failed" if sanitizer_notes else "passed",
         "evidence": "; ".join(sanitizer_notes) or "no script, embed or handler found"},
        {"name": "Responsive viewport meta tag", "method": "static",
         "result": "passed" if viewport else "failed", "evidence": str(viewport) if viewport else "missing"},
    ]


def review(html: str, acceptance_checks: list[dict]) -> tuple[list[dict], str | None]:
    if not acceptance_checks:
        return [], None
    listing = "\n".join(f"{i}. {c['text']}" for i, c in enumerate(acceptance_checks))
    try:
        out, model = llm.parse(SYSTEM, f"Acceptance checks:\n{listing}\n\nHTML:\n{html}", Review, effort="low")
    except Exception as exc:  # validation failure must not hide the artifact
        return [{"name": c["text"], "method": "model_review", "result": "not_run",
                 "evidence": f"review failed: {exc}"} for c in acceptance_checks], None
    by_index = {c.index: c for c in out.checks}
    results = []
    for i, c in enumerate(acceptance_checks):
        r = by_index.get(i)
        results.append({"name": c["text"], "method": "model_review", "sources": c.get("sources", []),
                        "result": r.result if r else "not_run",
                        "evidence": r.evidence if r else "reviewer returned no result"})
    return results, model
