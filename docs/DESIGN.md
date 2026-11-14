# PromptForge — Technical Design

How the scaffold implements the product in [README.md](../README.md). The README is the spec; if they disagree, the README wins and this file gets fixed. The earlier website-voting design is kept for reference in [archive/website-voting-design.md](archive/website-voting-design.md).

## Pipeline

```
request (typed, or spoken → ElevenLabs STT via POST /transcribe)
  1. intent     resolve project / document / feature; ask ONE question if ambiguous     agent/intent.py
  2. retrieve   scoped $vectorSearch over source chunks, current decisions,            agent/retrieve.py
                approved lessons (pre-filtered by repo/scope.py)
  3. brief      assemble cited brief; conflicts and unknowns → open_questions          agent/brief.py
  4. review     user edits / resolves questions → export Markdown, or execute
  5. execute    recheck cited memory revisions → model adapter → artifact              agent/execute.py
                → validation evidence (passed / failed / not_run)                      agent/validate.py
  6. learn      feedback → proposed lesson (dup/conflict check) → user approves        agent/learn.py
                with a scope → affects the next fresh run
```

## Data model

One Atlas database, `promptforge`. Every record carries `team_id`; project-level records also carry `project_id`.

| Collection | Key fields | Indexes |
|---|---|---|
| `users` | `_id, name, team_id, project_ids, role (member / publisher / admin)` | `team_id` |
| `projects` | `_id, team_id, name` | `team_id` |
| `sources` | `team_id, project_id, source_id, title, revision, chunk_index, text, embedding` | Vector Search (filters `team_id, project_id`); `{source_id, revision}` |
| `decisions` | `team_id, project_id, text, owner_id, revision, supersedes, status (current / superseded), embedding` | Vector Search (filters `team_id, project_id, status`) |
| `lessons` | `team_id, project_id, owner_id, scope (personal / project / team), text, revision, supersedes, status (proposed / approved / rejected / superseded / retired / expired), evidence_run_id, feedback_id, approved_by, task_tags, model, last_used_at, expires_at, purge_at, embedding` | Vector Search (filters `team_id, project_id, owner_id, scope, status`); TTL on `purge_at`; `{team_id, expires_at}` |
| `runs` | `team_id, project_id, user_id, request, brief {objective, requirements, current_decisions, implementation_context, preferences, acceptance_checks, open_questions}, provenance [{type, id, revision}], status (needs_clarification / draft / exported / executed / stale), model, artifact, checks [{name, result}], created_at` | `{team_id, project_id, created_at}` |
| `feedback` | `team_id, run_id, user_id, text, proposed_lesson_id, created_at` | `run_id` |
| `memory_events` | `record_type, record_id, team_id, event, actor, cause, before, after, at` | `{record_id, at}`; JSON Schema validation; insert-only |

## Governance rules in code

| README control | Where it lives |
|---|---|
| Access | `repo/scope.py` builds every pre-filter from the session (`lesson_filter`, `project_filter`). Lessons: own team AND approved AND (team scope OR this project OR own personal). Non-member project → `ScopeError` → 403 |
| Approval | `proposed` lessons are never retrieved. `repo.lessons.approve` checks the caller may publish at the chosen scope (team scope needs `publisher` or `admin`) |
| Attribution | `owner_id`, `approved_by`, `evidence_run_id`, `revision` on lessons; `owner_id`, `revision` on decisions; `provenance` on runs |
| Correction | New revision with `supersedes`; old one set to `superseded`. Only `current` decisions and `approved` lessons are retrieved |
| Expiry | `repo.lessons.expire_due` runs before every lesson read: sets `expired` and logs it. TTL on `purge_at` (= `expires_at` + 7 days) deletes later. Citing a lesson in an executed run pushes both forward |
| Index lag | Atlas Search indexes sync asynchronously, so vector hits for lessons and decisions are re-checked against the collection before use |
| Forgetting | Lesson removed from future use; runs citing it marked `stale`; event logged without the text. Not a complete erasure (README) |
| Run evidence | `runs.provenance`, `runs.model`, `runs.checks`. `execute` rechecks provenance revisions first and returns the change if any moved |

## API

All endpoints are under `/api`; the frontend is served at `/`.

| Method | Path | Does |
|---|---|---|
| GET | `/users` | Demo login picker (names and teams only) |
| POST | `/login` | `{user_id}` → session `{user_id, team_id, project_ids, role}` loaded from the database |
| GET | `/me` · POST `/logout` | Session |
| POST | `/transcribe` | Audio → ElevenLabs STT → `{text}` (key stays server-side, audio not stored, 10 MB cap) |
| GET | `/projects` | Caller's projects |
| GET | `/projects/{id}/context` | Sources, decisions (incl. superseded), visible lessons, recent runs |
| POST | `/projects/{id}/sources` | `{title, text, kind}`; same title → new revision (chunked + embedded) |
| POST | `/projects/{id}/decisions` | Add a team decision |
| POST | `/projects/decisions/{id}/supersede` | Correct a decision with a new revision |
| GET | `/projects/decisions/{id}/history` | Its memory events |
| POST | `/runs` | `{project_id, request}` → brief, or `needs_clarification` with one question |
| POST | `/runs/{id}/clarify` | `{answer}` → brief |
| GET | `/runs/{id}` | Run with brief, provenance, artifact, checks |
| POST | `/runs/{id}/answers` | `{answers: [{index, answer}]}` → brief rebuilt with the answers |
| PATCH | `/runs/{id}/brief` | `{brief}` user edits (citations re-validated) |
| POST | `/runs/{id}/refresh` | Re-retrieve current context and rebuild (after a stale recheck) |
| GET | `/runs/{id}/export` | Markdown brief with citations and provenance |
| POST | `/runs/{id}/execute` | Recheck (409 + changes if stale) → generate → checks |
| POST | `/runs/{id}/feedback` | `{text}` → proposed lesson (or "not reusable") |
| GET | `/lessons?project_id=&status=` | Lessons visible to caller |
| POST | `/lessons/{id}/approve` | `{scope, text?}` |
| POST | `/lessons/{id}/reject` · `/correct` · `/retire` | Lifecycle changes, each logged |
| DELETE | `/lessons/{id}` | Forget |
| GET | `/lessons/{id}/history` | Its memory events |

Errors: 401 not logged in, 403 scope/permission, 404 not found or not visible, 409 stale context or blocking questions, 400 invalid input.

## Open decisions

- **Demo task and artifact type.** Implemented for HTML pages (the leading candidate): generated HTML is sanitized server-side and renders in `<iframe sandbox="">`. The fixtures target a signup page.
- **Frontend.** `frontend/` follows the README experience (request → brief with context → result → feedback) with project context in a sidebar; no Streamlit, not a dashboard.
- **Insert-only role on the sandbox tier.** Verify custom roles are available; otherwise rely on code + JSON Schema and say so.
