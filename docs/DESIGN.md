# PromptForge technical design

The README defines setup and product behavior. This design supersedes the partner-only implementation; the team authorized an existing OpenAI API budget.

## Two request paths, one memory policy

- Direct: typed request or ElevenLabs transcription → `/api/build` → Voyage + Atlas retrieval → OpenAI Responses structured brief → review.
- Conversational: ElevenLabs Agent → scoped tool webhooks → saved brief → review. Browser SDK is loaded only when starting a conversation.
- Both: recheck citations, permissions, expiry and revisions → Markdown export or interactive OpenAI preview → recorded outcomes → proposed lesson → UI approval.

## Ownership

`repo/scope.py` defines retrieval scope. Runs are owner-private because their provenance may contain personal lessons. Browser sessions and agent tokens reload current user memberships. Logout invalidates agent tokens. Team lessons require publisher/admin permission. The demo user picker is not production authentication.

Sources use the same three visibility scopes before Atlas Vector Search: company (`team`) across a team, project within one project, and personal for one user across their projects. Any project member may add a personal source; publishers and admins may add project sources; only admins may add company sources. The demo Alice account is an admin. Existing sources without a scope are migrated to project scope. Source creation is recorded in the append-only memory event log.

`agent/brief.py` parses citation keys; `agent/recheck.py` checks cited records before handoff. Direct requests receive immutable U1 provenance for explicit user instructions. Invalid citations or uncited constraints block export; semantic entailment is not proven automatically.

`routes/build.py` owns direct briefs and preview generation. The generation lock prevents overlapping requests for one run. Cached previews belong to a brief revision and artifact version; edits invalidate them. Generated HTML may include inline client-side JavaScript. It runs in an opaque-origin iframe with script permission, while CSP blocks network requests, external assets, and form submissions. The preview has no backend integration.

`agent/llm.py` owns OpenAI calls: configurable models, bounded context/output, structured output, timeouts, no automatic retry, store=false. One failed request surfaces an actionable error. The frontend retries only on a new user action.

`routes/voice.py` provides bounded audio upload transcription and optional signed ElevenLabs agent sessions. Audio is not stored by this app. Provider retention follows the provider account settings.

## Memory lifecycle

Proposed → UI-approved at personal/project/team scope → corrected, retired, expired or forgotten. Read/export checks exclude expired records without relying on background TTL timing. Corrections use supersession. Forgetting marks affected runs stale; historical content is not fully erased. Events are append-only in app code; database-role enforcement must be configured separately.

Agent tools cannot approve. A source or model instruction cannot grant approval or choose an identity. Retrieved text is treated as untrusted data in the direct brief prompt. Approval endpoints use the current browser session.

## Services and credits

Atlas Sandbox stores state and memory; direct Voyage API handles embeddings/reranking; ElevenLabs handles dictation and live conversation; OpenAI handles direct briefs, lesson suggestions and preview generation; LangSmith records operation traces with inputs/outputs omitted. Credentials stay server-side. Exact event-credit coverage must be verified in each account.

## Remaining live verification

Configure keys, run doctor --live, initialize/seed the sandbox, run Atlas isolation tests, then exercise direct brief → clarification → export → preview → feedback → approve → new session. Separately verify microphone transcription and optional ElevenLabs tool callbacks over the tunnel. No live-provider pass is claimed by mocked tests.
