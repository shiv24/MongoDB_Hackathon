# PromptForge: notes for Claude

Hackathon project for Memory You Can Govern (Toronto, Nov 14, 2026; submissions close 5:00 PM). README.md is the product spec, and docs/DESIGN.md maps it to code. Read both before any non-trivial change. docs/archive/ holds the superseded website-voting design.

## Non-negotiables
- Identity and membership come from the session, never from a request body.
- All reads of lessons, decisions and sources go through `backend/app/repo/` and use a filter from `repo/scope.py`. Every `$vectorSearch` pre-filters on scope.
- `proposed` lessons never reach a brief. Only `approved` lessons and `current` decisions are retrieved.
- Runs are private to their creator; derived personal context must not be shared. Every brief instruction cites a revision. Preferences never override requirements; the direct demo records unresolved choices as explicit assumptions.
- `memory_events` is append-only. Every approval, correction, scope change, retirement, expiry and forget writes one.
- Lesson TTL is on `lessons.purge_at`; agent sessions also have an expiry TTL. Expiry is logged by the app sweep first.
- Stack: MongoDB Atlas, Voyage, ElevenLabs (dictation/live conversation), OpenAI Responses (direct briefs and preview generation), LangSmith. The user authorized the existing OpenAI API budget.
- The ElevenLabs agent reaches Atlas only through `routes/agent_tools.py`; identity comes from the `X-PF-Session` token (the `secret__pf_token` dynamic variable), never from tool arguments.
- API keys stay on the server.
- No Streamlit, and the main screen is not a dashboard. The frontend (`frontend/`) is plain HTML/JS served by FastAPI at `/`; the API is under `/api`. Insert server text with `textContent`, never `innerHTML`.

## Commands
- Run: `uvicorn app.main:app --reload --app-dir backend` (app at http://localhost:8000)
- Test: `pytest backend/tests` (offline; the live Atlas tests in `test_isolation.py` run when `.env` is set and fixtures are seeded)
- Atlas setup: `python scripts/setup_atlas.py`, then `python scripts/prepare_demo.py` (additive; do not reset existing data for routine setup)
- Agent setup: tunnel the app (`cloudflared tunnel --url http://localhost:8000`), set `PUBLIC_BASE_URL`, run `python scripts/setup_elevenlabs_agent.py`

## Skills
`skills/` (symlinked to `.claude/skills/`): brief-pipeline, governance-guardrails, atlas-setup, demo-prep.

- Agent tools may propose but cannot approve lessons. Approval uses the session-authenticated UI endpoint.
- Run `python scripts/doctor.py` for redacted configuration checks; `--live` probes providers.
