# PromptForge

An agent that builds websites from a one-line brief and gets measurably better each run. It remembers which prompt instructions won past votes.

**Track 2: Memory You Can Govern** (with vote auditing borrowed from Track 1).

- **Problem:** teams rewrite the same long prompts by hand. Nobody knows which instructions actually improve output, and prompt knowledge leaks or goes stale.
- **Solution:** each run pulls the team's best prompt "lessons" from Atlas Vector Search and condenses them into one short prompt. It generates two site variants and users vote. Votes update lesson scores: losers are demoted and winners shape the next run.
- **Proof:** run the same brief four times and you get a visibly better site with fewer prompt tokens. Every run records which memories it used.

Full design: [docs/DESIGN.md](docs/DESIGN.md)

## How it works

```
brief ──► 1. Retrieve   $vectorSearch on lessons (pre-filtered by team_id, status=active), re-rank 0.6·sim + 0.4·score
          2. Condense   Claude merges top lessons into one prompt (<150 words)
          3. Generate   Variant A (exploit) + Variant B (explore), in parallel
          4. Score      checklist auto-score 0–6
          5. Vote       user picks A/B + reason tags
          6. Update     Bayesian win rate, demote / retire / expire, log to memory_events
                        └──► scores feed step 1 on the next run
```

## Repo layout

```
backend/            FastAPI app
  app/main.py       app + routers
  app/routes/       /login, /runs, /lessons
  app/agent/        retrieve → condense → generate → score → memory update
  app/repo/         the ONLY data-access path to lessons (team isolation)
  tests/            isolation test and scoring tests
frontend/           plain HTML/JS: build-and-vote screen, lesson admin page
scripts/            Atlas setup (collections + indexes), seed data
docs/               design doc, demo script
skills/             Claude Code skills for this repo (symlinked into .claude/skills)
```

## Quickstart

```bash
cp .env.example .env            # fill in MONGODB_URI, ANTHROPIC_API_KEY, VOYAGE_API_KEY
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python scripts/setup_atlas.py   # collections, validators, Vector Search + TTL indexes
python scripts/seed.py          # demo users, two teams, starter lessons
uvicorn app.main:app --reload --app-dir backend
# open http://localhost:8000
```

## Team roles

| Role | Owns |
|---|---|
| P1 Generation | Claude client, condense, A/B generation, reason-tag → lesson |
| P2 Memory | Atlas setup, retrieval, scoring, demote/retire/expire, memory_events |
| P3 Frontend | Build screen, iframes, vote UI, memory sidebar, admin page |
| P4 Data & demo | Seeds, checklist scorer, isolation test, demo warm-up and script |

## Built during the hackathon

Everything in this repo was written on Nov 14, 2026, during the event. Components:

- [ ] FastAPI backend and agent loop
- [ ] Atlas collections, Vector Search index, TTL index, memory_events validator
- [ ] Lesson scoring, demotion, retirement and expiry
- [ ] Build-and-vote frontend and memory sidebar
- [ ] Lesson admin page
- [ ] Seed briefs and starter lessons (written by us)

**Third-party dependencies:** FastAPI, MongoDB Atlas, Anthropic Claude API, Voyage AI embeddings.

## License

MIT. See [LICENSE](LICENSE).
