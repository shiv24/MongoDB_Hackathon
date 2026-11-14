# PromptForge: notes for Claude

Hackathon project, built Nov 14, 2026 between 10:45 AM and 5:00 PM. The design is in docs/DESIGN.md; read it before any non-trivial change.

## Non-negotiables
- `team_id` always comes from the session, never from a request body.
- `backend/app/repo/lessons.py` is the only module that queries `lessons`. Every `$vectorSearch` pre-filters on `team_id`.
- `memory_events` is append-only. Every lesson change (steps 6–8) inserts a row with its `cause`.
- The ElevenLabs key never reaches the browser: audio goes to `/transcribe` on our backend, and audio is not stored.
- Generated HTML renders only in `<iframe sandbox="">`. No scripts.
- No Streamlit, and the main screen is not a dashboard. The frontend is plain HTML/JS served by FastAPI.

## Commands
- Run: `uvicorn app.main:app --reload --app-dir backend`
- Test: `pytest backend/tests`
- Atlas setup: `python scripts/setup_atlas.py`, then seed with `python scripts/seed.py`

## Skills
Repo skills live in `skills/` (symlinked to `.claude/skills/`): atlas-setup, memory-loop, governance-guardrails, demo-prep.
