# PromptForge technical design

The [README](../README.md) defines setup and product behavior. See the [frontend guide](FRONTEND.md) for browser state and interactions and the [demo guide](../DEMO.md) for the repeatable Admin console walkthrough.

## Two request paths, one memory policy

- Direct: typed request or ElevenLabs transcription → `/api/build` → Voyage + Atlas retrieval → OpenAI Responses structured brief → review.
- Conversational: ElevenLabs Agent → scoped tool webhooks → saved brief → review. The optional conversational backend is implemented separately; the current main screen exposes dictation, not a live agent conversation control.
- Both: recheck citations, permissions, expiry and revisions → Markdown export or interactive OpenAI preview → recorded outcomes → proposed lesson → UI approval.

## Ownership

`repo/scope.py` defines retrieval scope. Runs are owner-private because their provenance may contain personal lessons. Browser sessions and agent tokens reload current user memberships. Logout invalidates agent tokens. Team lessons require publisher/admin permission. The demo user picker is not production authentication.

Sources use the same three visibility scopes before Atlas Vector Search: company (`team`) across a team, project within one project, and personal for one user across their projects. Any project member may add a personal source; publishers and admins may add project sources; only admins may add company sources. The Admin console fixtures use Alice as publisher and Bob as member; the whole-team source option requires a separate admin identity. Existing sources without a scope are migrated to project scope. Source creation is recorded in the append-only memory event log.

`agent/brief.py` parses citation keys; `agent/recheck.py` checks cited records before handoff. Direct requests receive immutable U1 provenance for explicit user instructions. Invalid citations or uncited constraints block export; semantic entailment is not proven automatically.

`routes/build.py` owns direct briefs and preview generation. The generation lock prevents overlapping requests for one run. Cached previews belong to a brief revision and artifact version; edits invalidate them. Generated HTML may include inline client-side JavaScript. It runs in an opaque-origin iframe with script permission, while CSP blocks network requests, external assets, and form submissions. The preview has no backend integration.

`agent/llm.py` owns OpenAI calls: configurable models, bounded context/output, structured output, timeouts, no automatic retry, store=false. One failed request surfaces an actionable error. The frontend retries only on a new user action.

`routes/voice.py` provides bounded audio upload transcription and optional signed ElevenLabs agent sessions. Audio is not stored by this app. Provider retention follows the provider account settings.

## Repeatable demo

`POST /api/demo/start` requires a current session and copies the prepared template into a new team, project, and demo user. The starting run comes from `scripts/data/demo_baseline.json` and is labeled as a saved preview. Each round preserves original data and earlier rounds. `scripts/prepare_demo.py` additively prepares the template and curated Admin console sources.

Normal projects use scoped Atlas Vector Search. Isolated demo projects use direct scoped reads of their curated sources plus Voyage reranking to avoid waiting for copied sources to enter the search index. Explicitly selected lessons in an immediate feedback rebuild are checked for current status, authorization, project applicability, and expiry before inclusion; ordinary lesson retrieval uses search and a configurable reranker relevance threshold (`LESSON_RELEVANCE_MIN`, default `0.3`).

The primary feedback button saves and approves the user's exact instruction at the chosen scope before rebuilding. A separate suggestion path lets the user review model-proposed wording. Both use the authenticated lesson approval endpoint; neither grants agent tools approval authority.

## Memory lifecycle

Proposed → UI-approved at personal/project/team scope → corrected, retired, expired or forgotten. Read/export checks exclude expired records without relying on background TTL timing. Corrections use supersession. Forgetting marks affected runs stale; historical content is not fully erased. Events are append-only in app code; database-role enforcement must be configured separately.

Agent tools cannot approve. A source or model instruction cannot grant approval or choose an identity. Retrieved text is treated as untrusted data in the direct brief prompt. Approval endpoints use the current browser session.

## Services and credits

Atlas Sandbox stores state and memory; direct Voyage API handles embeddings/reranking; ElevenLabs handles dictation and live conversation; OpenAI handles direct briefs, lesson suggestions and preview generation; LangSmith records operation traces with inputs/outputs omitted. Credentials stay server-side. Exact event-credit coverage must be verified in each account.

## Remaining live verification

Configure keys, run `doctor --live`, initialize Atlas and prepare the demo, run Atlas isolation tests, then exercise request → brief with assumptions → export/preview → feedback → approval → fresh request. The rehearsal recorded in `DEMO.md` covers the direct flow; it does not verify every deployment or optional integration. Separately verify microphone transcription and optional ElevenLabs tool callbacks over the tunnel. No live-provider pass is claimed by mocked tests.
