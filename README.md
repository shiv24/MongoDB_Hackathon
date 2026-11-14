# PromptForge

**Say what you want to build. PromptForge brings the context your team already has.**

PromptForge turns a loose spoken or typed request into a grounded, inspectable brief for an AI model. It combines project sources, shared team decisions, and approved preferences so you spend less time reconstructing context and steering the same work again.

Review and export the brief to your coding tool, or run it with a selected model inside PromptForge. When you give feedback, PromptForge suggests a reusable lesson. You decide whether to save it for yourself, the project, or the team.

**Hackathon track:** Memory You Can Govern · MongoDB Agents in Context · Toronto, November 14, 2026.

> **Status:** Hackathon prototype. This README defines the current product direction and intended experience; direct and conversational workflows are implemented; live provider verification is pending. Website generation is a candidate first workflow, and the final demo is still to be chosen. See [implementation and limits](#implementation-and-limits) before running the project.

## The problem

AI-assisted teams repeatedly explain things their organization already knows: which spec is current, why an API changed, how the product should look, and what went wrong last time. That knowledge is scattered across documents, repositories, conversations, and individual agent sessions.

A capable model can still produce the wrong result when it receives an incomplete or outdated picture. Each teammate then spends time correcting work that another teammate has already explained.

PromptForge makes that context reusable, attributable, and correctable across sessions. Its first users are small product and engineering teams working with AI on a shared codebase or product.

The team's knowledge lives independently of any single conversation or model. Changing coding tools should not mean rebuilding the team's context from scratch.

## The product

**One request → relevant team context → an inspectable brief → a model result → approved learning.**

For example:

> “On that project doc, can we build the signup page? Keep it consistent with what we decided.”

The intended experience:

1. **Understand the request.** Resolve the project, document, and requested feature. If two documents or features fit, ask one focused question.
2. **Find the context.** Retrieve the relevant spec, current decisions, applicable code references, and approved preferences within the caller's access.
3. **Build the brief.** Explain the objective, requirements, constraints, dependencies, and acceptance checks. Cite sources and surface unresolved questions.
4. **Let the user inspect it.** Show which decisions and preferences shaped the brief. The user can edit it, export it, or send it to a configured model.
5. **Return work to review.** Present the generated artifact and available validation evidence. For a website, this could be a preview; for a code workflow, a diff and test results.
6. **Learn with permission.** Turn feedback such as “we always need a mobile layout” into a proposed lesson. The user chooses its scope before it affects future work.

The goal is a useful first result with fewer repeated corrections. Prompt length, token savings, and first-attempt success are measurements to evaluate, not guarantees.

An illustrative brief for that signup request might carry three distinct instructions: use the identity service named in the approved architecture decision, include the fields required by the current signup spec, and follow the project's approved button-label preference. Each instruction points back to its source. If the spec leaves a required field undefined, the brief surfaces that question before generation.

## What goes into a brief

The brief is the product's central artifact. It should be useful whether PromptForge executes it or another coding tool receives it.

| Part | What it contains |
| --- | --- |
| Objective | The user's intended outcome and the resolved project or feature |
| Requirements | Behavior the result must satisfy, with source references |
| Current decisions | Applicable decisions, their owners, and their revisions |
| Implementation context | Relevant interfaces, files, conventions, and dependencies when available |
| Preferences | Approved guidance selected for this user, project, task, and model |
| Acceptance checks | Concrete ways to determine whether the work meets the request |
| Open questions | Missing information, unresolved conflicts, and explicit assumptions |
| Provenance | The source and memory revisions used to assemble the brief |

PromptForge should preserve a requirement even when a shorter prompt would omit it. It should flag an unknown file or interface rather than invent one.

## Shared context and learned preferences

PromptForge keeps different kinds of knowledge distinct:

| Knowledge | Example | How it is maintained |
| --- | --- | --- |
| Source context | A feature spec or a repository snapshot | Linked to a source and revision; refreshed when that source changes |
| Team decisions | “The signup flow uses the existing identity service.” | Attributed to an authorized owner; corrected or superseded explicitly |
| Preferences | “For this project, use concise button labels.” | Suggested from feedback and approved at a chosen scope |
| Outcome evidence | A user's correction or a recorded check result | Attached to the run and the specific observation it supports |

**A preference does not silently override a requirement.** A newer chat message does not automatically supersede an approved decision. If applicable sources disagree and no authorized correction resolves them, PromptForge surfaces the conflict.

### Learning from feedback

The learning loop improves the context and instructions supplied to the model; it does not train the model's weights.

1. The user reviews a result and gives specific feedback.
2. PromptForge proposes a lesson, shows its evidence, and checks for a duplicate or conflicting memory.
3. The user approves, edits, or rejects the lesson and chooses its scope.
4. Future relevant requests can retrieve that approved lesson in a fresh session.
5. Later evidence can trigger a suggested correction, retirement, or re-evaluation.

Personal lessons guide that person's work. Project lessons apply to members of that project. Team lessons require permission to publish guidance for the team. Broader visibility always requires an explicit choice.

A vote for a whole artifact is a preference signal. It does not prove that every instruction used in that artifact caused the win. Where comparisons are used, capture a reason and keep the lesson tentative until approved. Track relevance and evidence by task and model instead of assuming a lesson works everywhere.

## Memory you can govern

MongoDB Atlas is the intended store for context, memory, and run state. Atlas Vector Search retrieves relevant meaning; application rules determine whether a memory is authorized, current, and applicable.

| Control | Required behavior |
| --- | --- |
| Access | Derive identity and membership from the session. Restrict retrieval to authorized team, project, and personal scopes before semantic search. Apply equivalent checks to source reads, run history, exports, and writes. |
| Approval | Keep suggested lessons separate from approved memory. Enforce who may publish or correct guidance at each scope. |
| Attribution | Record the source, author or approver, scope, revision, and supporting run where applicable. |
| Correction | Preserve explicit supersession relationships. Only the current authorized version may influence a new brief. |
| Expiry | Exclude expired memory when reading it. TTL cleanup alone is insufficient because deletion runs in the background. |
| Forgetting | Remove a memory from future use and invalidate affected derived context. Do not claim complete erasure while its text remains in stored briefs, events, or artifacts. |
| Run evidence | Record which source and memory revisions shaped a brief, which model received it, and what validation actually ran. |

Before execution, recheck the selected memory's current authorization, status, and revision against the authoritative records. If a decision changed after the brief was prepared, show the change and refresh the brief.

Correction and erasure have different retention needs. A correction may retain its history for explanation; an erasure workflow must address retained copies and derived content under an explicit retention policy. This prototype does not yet implement a complete erasure workflow.

References: [Atlas Vector Search filtering](https://www.mongodb.com/docs/vector-search/query/aggregation-stages/vector-search-stage/#mongodb-vector-search-filtering) and [MongoDB TTL behavior](https://www.mongodb.com/docs/manual/core/index-ttl/#behavior).

## The experience we are building

The main screen is a place to delegate work and review the result.

- **Project setup:** Supply a spec, relevant repository snapshot, and explicit decisions; review their source, owner, and scope. These establish the starting context before the first request.
- **Request:** Choose a project, speak or type a request, and review the transcript.
- **Context:** Inspect the selected sources, decisions, and preferences, with their attribution and scope.
- **Sources:** Add text, PDF, or UTF-8 text files with Company, Project, or User (Personal) visibility. The Admin console demo uses Alice (publisher) and Bob (member); members can publish personal sources, publishers can also publish project sources, and admins can publish at all three levels.
- **Brief:** PromptForge uses explicit assumptions instead of blocking questions; review the collapsible prompt if desired.
- **Result:** Inspect the generated artifact and validation evidence. A failed or unrun check remains visible.
- **Feedback:** Explain a correction and decide whether the proposed lesson should be remembered.

The brief should remain usable without an execution integration. Running it inside PromptForge is a second path through the same context and review flow.

## Hackathon scope

The product direction is settled: **shared team context plus approved learning, with both brief export and model execution.** The implemented output is an optional interactive website preview; Markdown export supports external coding workflows.

### First complete workflow

- One project with a small, curated set of source documents and explicit team decisions.
- Typed requests, with voice input when the core loop works.
- Atlas-backed memory and Vector Search with enforced access scopes.
- A cited brief that can be reviewed and exported.
- One configured generation model and one supported artifact type.
- Feedback that becomes a suggested lesson with an explicit scope and approval.
- A fresh run showing an approved lesson or corrected decision affecting the result.
- A second team's fixtures to verify isolation.

Start with supplied documents and repository snapshots. Live ingestion of everyone's agent sessions is a later integration, with explicit connection and sharing controls.

### Later expansion

The full product includes model selection; the first complete workflow only needs one working adapter. Later expansion adds more adapters, live document and repository connectors, coding-tool handoff, automated validation for more artifact types, and broader learning from outcome evidence. A/B generation is an optional way to gather feedback; it is not required for the core workflow.

## How we will prove it works

The demo should establish a visible connection between a memory change and a result. Its exact task is still to be chosen.

1. Run a fixed request and show the sources and memories used.
2. Approve a specific lesson or correct a team decision in a separate session.
3. Repeat the same request in a fresh session, using the same model configuration and starting artifact or repository revision.
4. Show the changed brief, the cited memory revision, and an observable difference in the result.
5. Verify that expired, superseded, unapproved, and unauthorized memories are excluded.

Use a requirement or distinctive project preference with a concrete check. Do not rely on a general claim that the second result looks better. Repeated trials and a memory-disabled comparison can help distinguish the effect from generation variance; a single pair of outputs is demo evidence, not a causal benchmark.

We will report requirement satisfaction, retained constraints, user corrections, time to a reviewable result, and validation outcomes. Any token or latency comparison must state its baseline. Fixtures and prerecorded fallback runs must be identified as such.

## Run locally

Python 3.10+ is required. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python scripts/init_env.py
```

Edit `.env` locally. Required for direct briefs and previews: `MONGODB_URI` (the event sandbox), `VOYAGE_API_KEY` (direct Voyage account), and `OPENAI_API_KEY`. Default brief and generation model: `gpt-4.1-mini`; override with `OPENAI_BRIEF_MODEL` and `OPENAI_GENERATION_MODEL` if your project supports another Responses structured-output model.

Add `ELEVENLABS_API_KEY` for microphone dictation. `ELEVENLABS_STT_MODEL` defaults to `scribe_v2`. Enable LangSmith only after setting `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true`. Traces omit operation inputs/outputs to avoid copying personal context; usage is recorded on runs/artifacts.

```bash
python scripts/doctor.py
python scripts/doctor.py --live
python scripts/setup_atlas.py
python scripts/prepare_demo.py
uvicorn app.main:app --reload --app-dir backend
```

The showcase seed is additive and safe to rerun; it creates the Admin console sources and decisions without pre-approving lessons.

Open http://localhost:8000, type a request, and click **Build preview**. PromptForge chooses reasonable defaults, shows the artifact first, and keeps the grounded prompt collapsible. Record outcomes and approve suggested lessons explicitly.

`doctor --live` tests connectivity and model access; its Voyage embedding probe consumes a small number of tokens. It does not prove the full workflow. Setup must finish with all three vector indexes READY. Allow time for freshly seeded data to be indexed. Atlas also needs your client IP allowed and a database user with appropriate permissions.

Seeding an existing database stops rather than overwriting it. `python scripts/seed.py --reset` deliberately deletes the demo database's application records. Use only when you intend to reset demo data.

### Optional ElevenLabs live conversation

The direct workflow and dictation need no tunnel. For full back-and-forth conversation:

```bash
cloudflared tunnel --url http://localhost:8000
```

Put the HTTPS URL in `PUBLIC_BASE_URL`, then run:

```bash
python scripts/setup_elevenlabs_agent.py
```

Put the printed ID in `ELEVENLABS_AGENT_ID` and restart the app. Click **Live voice conversation**. The agent retrieves context and saves briefs through scoped webhook tools. It can propose a lesson; the user must click **review proposal → Approve lesson** in the app. It cannot approve via its webhook.

Keep the tunnel running. If the URL changes, rerun setup (it creates new agent/tools) and update the ID. ElevenLabs agent/model usage has its own billing; verify event-coupon coverage in your account. No free-generation guarantee is made.

## Implementation and limits

- Both ElevenLabs conversation and direct OpenAI briefs use Atlas context and the same export checks.
- Voyage embeds and reranks context. The backend controls scope, current status, expiry, and permissions.
- Runs are private to their creator, including derived personal context. Shared lessons remain available according to their approved scope.
- Expired, retired, superseded, removed, or unauthorized cited memory blocks export/generation. Uncited requirements and invalid citations block export. Citation validation verifies references, not semantic truth.
- OpenAI returns typed structured output. Requests have bounded output/context, timeouts, and no automatic OpenAI retries. Preview generation is locked per run, cached per brief revision, and rechecks memory after generation.
- Website output is a self-contained HTML/CSS/JavaScript prototype. Inline interactions run in an isolated iframe; external assets, network calls, and form submission are blocked. Backend features are not implemented by this preview, and generated behavior should be reviewed before relying on it.
- Checks are user-reported. There is no claim of automatic functional correctness or complete erasure of previously exported content.
- The demo login picker is simulated identity, not production authentication. Use synthetic demo data; replace demo login before real-team/public production use.
- LangSmith tracing is optional. OpenAI usage is stored with model results; dollar spend depends on your configured models. Set provider-side spending limits for your budget.

## Verification

```bash
# Explicitly disable live credentials for the offline suite:
MONGODB_URI='' VOYAGE_API_KEY='' LANGSMITH_TRACING=false pytest backend/tests -q
node --check frontend/app.js
# After configuring and seeding the sandbox:
pytest backend/tests/test_isolation.py -q
```

Current offline result: **53 backend tests passed, 3 live Atlas tests skipped; 4 frontend sandbox tests passed**. Run the frontend tests with `node --test frontend/tests/preview.test.mjs`. A headless browser confirmed Alice sees the three source visibility choices; perform the full manual workflow below after setup.

Offline tests cover API flow, scopes, lifecycle, private runs, stale/expired memory, explicit approval boundaries, direct generation with mocked providers, preview caching and sanitization. Live provider calls and real browser microphone/agent behavior still require credentials and a live smoke test.

## Demo acceptance

1. Alice requests a signup page, answers the missing company-size question, and inspects source citations.
2. Export or generate a preview and record what actually meets the checks.
3. Propose and approve a project lesson; Bob's fresh request includes it. Alice's personal lessons stay private.
4. Correct a decision; the old brief is blocked until refreshed.
5. Switch to Orbit and verify its context stays isolated.

## License

MIT. See [LICENSE](LICENSE).
