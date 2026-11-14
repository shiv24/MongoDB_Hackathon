# PromptForge — Technical Design

How the scaffold implements the product in [README.md](../README.md). The README is the spec; if they disagree, the README wins and this file gets fixed. The earlier website-voting design is kept for reference in [archive/website-voting-design.md](archive/website-voting-design.md).

## Stack

MongoDB Atlas plus the event's partner resources only: **ElevenLabs Agents** (conversation and the only LLM), **Voyage AI** (embeddings, reranking), **LangSmith** (tracing). No other model APIs.

## Pipeline

```
user  ⇄ ElevenLabs agent (voice or text, private agent started with a signed URL from POST /api/voice/session)
  1. clarify      agent asks ONE question if two documents/features fit                (agent prompt)
  2. context      tool get_project_context → scoped $vectorSearch + Voyage rerank      routes/agent_tools.py → agent/retrieve.py
  3. brief        tool save_brief → citations validated, run updated; UI polls it      agent/brief.py, agent/pipeline.py
  4. review       user edits / answers questions (answers go back to the agent)
  5. export       recheck cited memory (stale → 409 + changes) → Markdown for Claude Code   agent/recheck.py
  6. result       user records acceptance-check outcomes (outcome evidence)
  7. learn        tool record_feedback → proposed lesson; approve_lesson only after an explicit yes
```

**Identity for tool calls.** `POST /api/voice/session` (logged-in user, project member) mints a random token, stores only its SHA-256 hash in `agent_sessions` (TTL 2 h), and returns it with the signed URL. The browser passes it as the dynamic variable `secret__pf_token`; ElevenLabs substitutes it into the `X-PF-Session` header of every tool call and never sends it to the LLM. `routes/agent_tools.py` resolves the token to the user's session, so the model cannot choose a team, project or user. An optional `AGENT_TOOL_SECRET` header adds a shared secret.

## Data model

One Atlas database, `promptforge`. Every record carries `team_id`; project-level records also carry `project_id`.

| Collection | Key fields | Indexes |
|---|---|---|
| `users` | `_id, name, team_id, project_ids, role (member / publisher / admin)` | `team_id` |
| `projects` | `_id, team_id, name` | `team_id` |
| `sources` | `team_id, project_id, source_id, title, revision, chunk_index, text, embedding` | Vector Search (filters `team_id, project_id`); `{source_id, revision}` |
| `decisions` | `team_id, project_id, text, owner_id, revision, supersedes, status (current / superseded), embedding` | Vector Search (filters `team_id, project_id, status`) |
| `lessons` | `team_id, project_id, owner_id, scope (personal / project / team), text, revision, supersedes, status (proposed / approved / rejected / superseded / retired / expired), evidence_run_id, feedback_id, approved_by, task_tags, model, last_used_at, expires_at, purge_at, embedding` | Vector Search (filters `team_id, project_id, owner_id, scope, status`); TTL on `purge_at`; `{team_id, expires_at}` |
| `runs` | `team_id, project_id, user_id, request, author {kind: elevenlabs_agent, conversation_id}, brief {objective, requirements, current_decisions, implementation_context, preferences, acceptance_checks, open_questions, assumptions}, brief_revision, answers, provenance [{key, type, id, revision}], status (drafting / needs_answers / draft / stale / exported / reviewed), checks [{name, result, method: user_review, evidence}], outcome, created_at` | `{team_id, project_id, created_at}`; `provenance.id` |
| `agent_sessions` | `token_hash, session, project_id, current_run_id, expires_at` | unique `token_hash`; TTL on `expires_at` |
| `feedback` | `team_id, run_id, user_id, text, proposed_lesson_id, created_at` | `run_id` |
| `memory_events` | `record_type, record_id, team_id, event, actor, cause, before, after, at` | `{record_id, at}`; JSON Schema validation; insert-only |

## Governance rules in code

| README control | Where it lives |
|---|---|
| Access | `repo/scope.py` builds every pre-filter from the session (`lesson_filter`, `project_filter`). Lessons: own team AND approved AND (team scope OR this project OR own personal). Non-member project → `ScopeError` → 403 |
| Approval | `proposed` lessons are never retrieved. `repo.lessons.approve` checks the caller may publish at the chosen scope (team scope needs `publisher` or `admin`) |
| Attribution | `owner_id`, `approved_by`, `evidence_run_id`, `revision` on lessons; `owner_id`, `revision` on decisions; `provenance` on runs |
| Correction | New revision with `supersedes`; old one set to `superseded`. Only `current` decisions and `approved` lessons are retrieved |
| Expiry | `repo.lessons.expire_due` runs before every lesson read: sets `expired` and logs it. TTL on `purge_at` (= `expires_at` + 7 days) deletes later. Citing a lesson in an exported brief pushes both forward |
| Index lag | Atlas Search indexes sync asynchronously, so vector hits for lessons and decisions are re-checked against the collection before use |
| Forgetting | Lesson removed from future use; runs citing it marked `stale`; event logged without the text. Not a complete erasure (README) |
| Run evidence | `runs.provenance`, `runs.author` (agent conversation id), `runs.checks` (user-reported, labelled `user_review`), LangSmith traces. `export` rechecks provenance revisions first and returns the change if any moved |

## API

All endpoints are under `/api`; the frontend is served at `/`.

**UI (session cookie)**

| Method | Path | Does |
|---|---|---|
| GET | `/users` · POST `/login` · GET `/me` · POST `/logout` | Demo login; session loaded from the database |
| POST | `/voice/session` | `{project_id}` → `{agent_session_id, signed_url, dynamic_variables}` for the ElevenLabs agent |
| GET | `/voice/session/{id}/run` | The run the agent is currently drafting (UI polls it) |
| GET | `/projects` · `/projects/{id}/context` | Projects; sources, decisions, visible lessons, recent runs |
| POST | `/projects/{id}/sources` · `/projects/{id}/decisions` · `/projects/decisions/{id}/supersede` | Project setup and correction |
| GET | `/projects/decisions/{id}/history` · `/lessons/{id}/history` | Memory events |
| GET | `/runs/{id}` · PATCH `/runs/{id}/brief` | Run; user edits (citations re-validated) |
| GET | `/runs/{id}/export` | Recheck → Markdown (409 with `changes` or `blocking_questions`) |
| POST | `/runs/{id}/outcome` | `{results: [{index, result, evidence}], tool}` |
| POST | `/runs/{id}/feedback` | `{text, lesson?}` → proposed lesson |
| GET | `/lessons?project_id=&status=` · POST `/lessons/{id}/approve|reject|correct|retire` · DELETE `/lessons/{id}` | Lesson lifecycle |

**Agent tools (header `X-PF-Session`, optional `X-PF-Agent-Key`)**

| Tool | Path | Does |
|---|---|---|
| `get_project_context` | POST `/agent/context` | `{request, search_query}` → `run_id` + keyed context `[S#] [D#] [L#]` |
| `save_brief` | POST `/agent/brief` | `{run_id, objective, requirements[], …, blocking_questions[], resolved_questions[]}` |
| `record_feedback` | POST `/agent/feedback` | `{run_id, feedback, lesson?, conflicts[]}` → proposed lesson + allowed scopes |
| `approve_lesson` / `reject_lesson` | POST `/agent/lessons/approve|reject` | `{lesson_id, scope}` |

Errors: 401 not logged in / bad token, 403 scope or permission, 404 not found or not visible, 409 stale context or blocking questions, 400 invalid input, 503 missing configuration.

## Open decisions

- **In-app execution.** Not built: no partner credit covers generation, so the brief is exported to the user's coding tool.
- **Agent LLM.** `ELEVENLABS_AGENT_LLM` (default `claude-sonnet-5-5`) runs inside ElevenLabs on ElevenLabs credits; any model on ElevenLabs' list works.
- **Insert-only role on the sandbox tier.** Verify custom roles are available; otherwise rely on code + JSON Schema and say so.
