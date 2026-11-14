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
| Expiry | `repo.lessons.expire_due` runs before every lesson read: sets `expired` and logs it. TTL on `purge_at` (= `expires_at` + 7 days) deletes later |
| Forgetting | Lesson removed from future use; runs citing it marked `stale`; event logged without the text. Not a complete erasure (README) |
| Run evidence | `runs.provenance`, `runs.model`, `runs.checks`. `execute` rechecks provenance revisions first and returns the change if any moved |

## API

| Method | Path | Does |
|---|---|---|
| POST | `/login` | Pick a demo user → session `{user_id, team_id, project_ids, role}` |
| POST | `/transcribe` | Audio → ElevenLabs STT → `{text}` (key stays server-side, audio not stored) |
| GET | `/projects` | Caller's projects |
| GET | `/projects/{id}/context` | Sources, current decisions, visible approved lessons with owner, scope, revision |
| POST | `/projects/{id}/sources` | Add a spec or repo snapshot (chunked + embedded) |
| POST | `/projects/{id}/decisions` | Add a team decision |
| POST | `/projects/decisions/{id}/supersede` | Correct a decision with a new revision |
| POST | `/runs` | `{project_id, request}` → brief, or a clarifying question |
| GET | `/runs/{id}` | Run with brief, provenance, artifact, checks |
| PATCH | `/runs/{id}/brief` | Edit brief / answer open questions |
| GET | `/runs/{id}/export` | Markdown brief with citations |
| POST | `/runs/{id}/execute` | Recheck → model → artifact + checks |
| POST | `/runs/{id}/feedback` | Feedback → proposed lesson |
| GET | `/lessons?project_id=&status=` | Lessons visible to caller |
| POST | `/lessons/{id}/approve` | `{scope, text?}` |
| POST | `/lessons/{id}/reject` · `/correct` · `/retire` | Lifecycle changes, each logged |
| DELETE | `/lessons/{id}` | Forget |

## Open decisions

- **Demo task and artifact type.** Website generation is the leading candidate. If chosen, generated HTML renders in `<iframe sandbox="">` with no scripts.
- **Frontend.** Not built yet. Must follow the README experience (request → context → brief → result → feedback); no Streamlit, not a dashboard.
- **Insert-only role on the sandbox tier.** Verify custom roles are available; otherwise rely on code + JSON Schema and say so.
