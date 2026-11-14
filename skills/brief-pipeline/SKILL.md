---
name: brief-pipeline
description: PromptForge's request → context → cited brief → execute → learn pipeline and its rules. Use when implementing or changing anything in backend/app/agent/, brief assembly, execution, or turning feedback into lessons.
---

# Brief pipeline

Spec: README.md. Code map: docs/DESIGN.md "Pipeline".

| Step | Module | Rule |
|---|---|---|
| Intent | `intent.py` | Resolve project, document, feature. Two plausible matches → return ONE clarifying question, status `needs_clarification` |
| Retrieve | `retrieve.py` | Embed request; search source chunks, `current` decisions, `approved` lessons through `repo/` only. Scope pre-filters come from `repo/scope.py` |
| Brief | `brief.py` | Sections: objective, requirements, current_decisions, implementation_context, preferences, acceptance_checks, open_questions, provenance |
| Execute | `execute.py` | Recheck every provenance entry's current status and revision first. Anything changed → stop, mark run `stale`, return the change |
| Validate | `validate.py` | Each acceptance check → `passed` / `failed` / `not_run`. Never hide failed or unrun checks |
| Learn | `learn.py` | Feedback → one proposed lesson with evidence; flag duplicates (similarity > 0.92) and conflicts. Not used until approved with a scope |

## Brief rules
- Every instruction cites a source chunk, decision or lesson **revision**.
- A preference never overrides a requirement. A newer chat message never supersedes an approved decision. Unresolved conflict → `open_questions`.
- Keep every requirement even if it makes the brief longer.
- Unknown file or interface → flag it; never invent one.
- The exported Markdown must be usable in another coding tool with no PromptForge context.

## Learning rules
- Learning changes the context given to the model, not model weights.
- A vote or thumbs-up on a whole artifact is a preference signal, not proof that each lesson caused it. Keep lessons tentative until a person approves them.
- Track `task_tags` and `model` on lessons; do not assume a lesson works everywhere.
