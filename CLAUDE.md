# PromptForge: notes for Claude

Hackathon project for Memory You Can Govern (Toronto, Nov 14, 2026; submissions close 5:00 PM). README.md is the product spec, and docs/DESIGN.md maps it to code. Read both before any non-trivial change. docs/archive/ holds the superseded website-voting design.

## Non-negotiables
- Identity and membership come from the session, never from a request body.
- All reads of lessons, decisions and sources go through `backend/app/repo/` and use a filter from `repo/scope.py`. Every `$vectorSearch` pre-filters on scope.
- `proposed` lessons never reach a brief. Only `approved` lessons and `current` decisions are retrieved.
- Every brief instruction cites a revision. Preferences never override requirements, and conflicts go to `open_questions`.
- `memory_events` is append-only. Every approval, correction, scope change, retirement, expiry and forget writes one.
- The only TTL index is on `lessons.purge_at`. Expiry is logged by the app sweep first.
- API keys (Anthropic, Voyage, ElevenLabs) stay on the server. Audio is not stored.
- Any generated HTML renders only in `<iframe sandbox="">`.
- No Streamlit, and the main screen is not a dashboard. The frontend (`frontend/`) is plain HTML/JS served by FastAPI at `/`; the API is under `/api`. Insert server text with `textContent`, never `innerHTML`.

## Commands
- Run: `uvicorn app.main:app --reload --app-dir backend` (app at http://localhost:8000)
- Test: `pytest backend/tests` (offline; the live Atlas tests in `test_isolation.py` run when `.env` is set and fixtures are seeded)
- Atlas setup: `python scripts/setup_atlas.py`, then `python scripts/seed.py --reset`

## Skills
`skills/` (symlinked to `.claude/skills/`): brief-pipeline, governance-guardrails, atlas-setup, demo-prep.
