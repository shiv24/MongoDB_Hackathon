---
name: governance-guardrails
description: PromptForge's access-scope, approval, correction, expiry, forgetting and run-evidence invariants. Use before writing or reviewing any route, query, or lifecycle action that touches sources, decisions, lessons, runs, feedback or memory_events.
---

# Governance guardrails

Check every change against these. They are the README's "Memory you can govern" table, in code terms.

## Access
- [ ] Identity and membership come from `request.session` only, never from a body, query string or path.
- [ ] Every read of lessons, decisions or sources uses a filter from `backend/app/repo/scope.py`. A project the user isn't a member of raises `ScopeError` → 403.
- [ ] Scope filters go in `$vectorSearch.filter` (a pre-filter), never in a later `$match`.
- [ ] Run history, exports and feedback check the same team and project membership.
- [ ] `backend/tests/test_scope.py` passes; `test_isolation.py` (team_b sees zero team_a ids) once Atlas fixtures exist.

## Approval and attribution
- [ ] `proposed` lessons are never retrieved into a brief.
- [ ] Approving at `team` scope requires `publisher` or `admin`; `project` scope requires project membership.
- [ ] Lessons record `owner_id`, `approved_by`, `evidence_run_id`, `revision`. Decisions record `owner_id`, `revision`.

## Correction, expiry, forgetting
- [ ] Correction = new revision with `supersedes`; old one set to `superseded`. Only current versions are retrieved.
- [ ] `expire_due` runs before lesson reads and logs `expired`. The only TTL index is on `purge_at`.
- [ ] Forget removes the lesson from future use, marks citing runs `stale`, and logs an event **without** the text. Never claim complete erasure.

## Evidence
- [ ] `memory_events` gets inserts only, with no update or delete anywhere.
- [ ] Runs store provenance revisions, the model, and every check result, including `failed` and `not_run`.
- [ ] `execute` rechecks provenance before calling the model.

## Secrets and rendering
- [ ] API keys (Anthropic, Voyage, ElevenLabs) never reach the browser.
- [ ] Any generated HTML renders only in `<iframe sandbox="">`.
