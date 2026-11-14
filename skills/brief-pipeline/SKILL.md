---
name: brief-pipeline
description: PromptForge's ElevenLabs-agent pipeline (context tool → cited brief → export → outcome → feedback → approved lesson) and its rules. Use when changing the agent prompt or tools (scripts/setup_elevenlabs_agent.py, backend/app/routes/agent_tools.py), brief parsing/export, or lesson proposals.
---

# Brief pipeline

Spec: README.md. Code map: docs/DESIGN.md "Pipeline". Stack is Atlas + partner resources only (ElevenLabs, Voyage, LangSmith): do not add other model APIs.

| Step | Where | Rule |
|---|---|---|
| Clarify | agent prompt | Ask ONE question only if two documents/features plausibly fit |
| Context | `get_project_context` → `pipeline.start_draft` → `retrieve.gather` | Scoped `$vectorSearch` + Voyage rerank; returns keyed `[S#] [D#] [L#]` context and a `run_id` |
| Brief | `save_brief` → `brief.from_agent` + `validate_citations` | Items are strings ending in citation keys; unknown keys dropped, uncited flagged; blocking questions → `needs_answers` |
| Export | `pipeline.export` → `recheck.recheck` | Cited memory changed → 409 with `changes`, run `stale`; otherwise Markdown with provenance |
| Result | `pipeline.record_outcome` | User-reported per acceptance check, `method: user_review`; unmarked = `not_run` |
| Learn | `record_feedback` → `pipeline.feedback` | Proposes; never approves. `approve_lesson` only after an explicit yes |

## Brief rules (also in the agent prompt; keep them in sync)
- Every instruction cites a source chunk, decision or lesson key.
- A preference never overrides a requirement; conversation never silently supersedes a decision; conflicts → questions.
- Keep every requirement. Never invent files or interfaces.

## Changing tools
Tool JSON lives in `scripts/setup_elevenlabs_agent.py`; the matching pydantic bodies in `routes/agent_tools.py`. Change both, then re-run the setup script (it creates a fresh agent and prints the new `ELEVENLABS_AGENT_ID`).
