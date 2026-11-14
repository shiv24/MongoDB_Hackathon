# PromptForge — Design Doc

Nov 14, 2026 · @Ethan

## Overview

PromptForge is an agent that builds websites from a one-line brief and gets measurably better each run, because it remembers which prompt instructions won past votes. It targets **Track 2: Memory You Can Govern**, with vote auditing borrowed from Track 1.

- **Problem:** teams rewrite the same long prompts by hand. Nobody knows which instructions actually improve output, and prompt knowledge leaks or goes stale.
- **Solution:** each run retrieves the team's best prompt "lessons" from Atlas Vector Search and condenses them into one short prompt. It generates two site variants and lets users vote. Votes update lesson scores: losers are demoted and winners shape the next run.
- **Proof:** the same brief, run four times, produces a visibly better site with fewer prompt tokens. Every run records which memories it used.
- **Constraints:** ~6 hours of build time (10:45 AM–5:00 PM), up to 4 people, MongoDB Atlas Sandbox, public repo, all work new.

## Requirements compliance

| Rule | How PromptForge meets it |
|---|---|
| Use the MongoDB Atlas Sandbox (finalists) | All collections, Vector Search and TTL indexes live in the hackathon sandbox project from the invite email; set up in hour 1 |
| Public repo | Public from the first commit; MIT license |
| New work only | Repo created at 10:45 AM; frequent commits; README "Built during the hackathon" lists every component |
| Demo shows only our work | Demo walks through our pipeline, memory scoring and voting UI; FastAPI, Claude API and Voyage named as dependencies |
| Rights to code, data, assets | No stock images; placeholders are CSS shapes or CC0 assets; seed briefs written by us |
| Max 4 members | Roles sized for 4; works with 2–3 by merging roles |
| Not basic RAG | Retrieval is one step. The agent also generates, scores, demotes and expires, and memory measurably changes the next run |
| Not Streamlit | Plain HTML/JS (or React) frontend served by FastAPI |
| Not dashboard-first | Main screen is the side-by-side build-and-vote flow; memory panel is a sidebar |
| No banned categories | Website generation is not health, education, hiring, sports, personality or image analysis |

## Architecture

Three parts: a plain web frontend, a FastAPI agent running a four-step loop, and MongoDB Atlas as the memory and audit store. Claude (condense, generate) and Voyage AI (embeddings) are the only external APIs.

Step 4 rewrites lesson scores and appends to `memory_events`. Step 1 reads those scores on the next run, which closes the learning loop.

## Data model

Five collections in one Atlas database, `promptforge`. Lessons are the memory; runs and votes are the audit trail that proves memory changed behavior.

| Collection | Purpose | Key fields | Indexes |
|---|---|---|---|
| `users` | Identity and team membership | `_id, name, team_id, role (member/expert/admin), vote_weight` | `team_id` |
| `lessons` | Reusable prompt instructions (the memory) | `team_id, text, embedding, category, score, wins, losses, status (active/demoted/retired), model_version, source_run_id, created_by, expires_at` | Vector Search on `embedding` with filters `team_id, status`; TTL on `expires_at`; `{team_id, score}` |
| `runs` | One generation per brief | `team_id, user_id, brief, brief_embedding, used_lessons, condensed_prompt, tokens_raw, tokens_condensed, variants [{id, lesson_ids, prompt, html, checklist_score}], status, created_at` | `{team_id, created_at}` |
| `votes` | Who preferred which variant and why | `run_id, user_id, team_id, winner, reasons [tags], weight, created_at` | Unique `{run_id, user_id}` |
| `memory_events` | Append-only log of every lesson change | `lesson_id, team_id, event (created/promoted/demoted/retired/corrected/forgotten/expired), actor, cause (vote id/admin/ttl), before, after, at` | `{lesson_id, at}`; JSON Schema validation; app role insert-only |

Vector Search index on `lessons`:

```json
{
  "fields": [
    {"type": "vector", "path": "embedding", "numDimensions": 1024, "similarity": "cosine"},
    {"type": "filter", "path": "team_id"},
    {"type": "filter", "path": "status"},
    {"type": "filter", "path": "category"}
  ]
}
```

Set `numDimensions` to whatever the embedding model returns (1024 for Voyage `voyage-3`).

## Core algorithms

One run = retrieve, condense, generate two variants, score, vote, update memory.

1. **Retrieve.** Embed the brief. `$vectorSearch` on lessons with `filter: {team_id, status: "active"}, limit: 8`. Re-rank by `0.6 × similarity + 0.4 × score`.
2. **Condense.** Send top lessons to Claude: "merge into one prompt under 150 words, drop duplicates and contradictions, keep imperative instructions." Store `tokens_raw` vs `tokens_condensed`.
3. **Generate two variants.**
   - Variant A (exploit): condensed prompt from top lessons.
   - Variant B (explore): swaps in 1–2 lower-ranked or new lessons so untested ideas get a chance.
   - Each returns one self-contained HTML file, rendered in a sandboxed iframe.
4. **Auto-score.** Fixed checklist parsed from the HTML: hero heading, one primary CTA, responsive meta tag, ≤ 4 colors, alt text on images, a nav. Objective 0–6.
5. **Vote.** User picks A or B and taps reason tags ("clear CTA", "too cluttered"…).
6. **Update memory.**
   - Winning-variant lessons: `wins += weight`; losers: `losses += weight`.
   - `score = (wins + 1) / (wins + losses + 2)` (new lessons start at 0.5).
   - Winner reason tags become a candidate lesson (Claude turns "clear CTA" into an instruction), deduped by vector similarity > 0.92.
7. **Demote and retire.** `score < 0.35` after ≥ 4 votes → demoted (Variant B only). `score < 0.2` after ≥ 6 votes → retired (excluded from retrieval).
8. **Expire.** `expires_at` = 30 days after last win; a win pushes it forward. Lessons with a different `model_version` are re-queued as demoted for re-testing.

Every step 6–8 change writes a `memory_events` row with its cause.

## Governance

### 1. No leakage between teams
- `team_id` comes from the authenticated session, never the request body.
- Every `$vectorSearch` carries `filter: {team_id}` as a pre-filter, so other teams' lessons are never scored, not just hidden.
- `get_lessons(team_id, ...)` is the only path to lessons; a unit test asserts a Team B query returns zero Team A ids.
- Demo: same brief on Team A and Team B → different styles, disjoint lesson ids.

### 2. Correcting and forgetting
- **Automatic:** demote/retire by score; TTL expiry; model-version change forces re-testing.
- **Manual:** admin can mark wrong (retire, `cause = admin`), edit (new text + re-embed, old text kept in `memory_events.before`), or forget (hard delete, event logged without the text).
- Retired and forgotten lessons are excluded by the status filter.

### 3. Proving memory changed behavior
- Each run stores `used_lessons` and per-variant `lesson_ids`.
- Memory-off control toggle: compare checklist score and votes for memory-on vs memory-off.
- Counterfactual: forget the top lesson, rerun, show the site loses that feature.

### Vote integrity
- Unique index on `{run_id, user_id}`.
- Weight from `users.vote_weight` (expert = 2), copied onto the vote.
- `memory_events` is append-only (insert-only role + JSON Schema), so any score can be rebuilt from votes.

## API and screens

| Method | Path | Does |
|---|---|---|
| POST | `/login` | Pick a demo user; sets session with `user_id, team_id` |
| POST | `/runs` | Body `{brief, memory: true}`; retrieve, condense, generate A and B |
| GET | `/runs/{id}` | Run detail incl. `used_lessons` and token savings |
| POST | `/runs/{id}/vote` | Body `{winner, reasons}`; records vote, updates lessons, returns deltas |
| GET | `/lessons` | Team's lessons by score |
| PATCH | `/lessons/{id}` | Admin: edit text, or mark wrong |
| DELETE | `/lessons/{id}` | Admin: forget |

**Screens**
1. **Build (main):** brief input, memory toggle, two iframes side by side, checklist score under each, vote buttons + reason tags.
2. **Memory sidebar:** lessons used with score bars, live "+0.08" / "−0.05" deltas after each vote.
3. **Lesson admin:** edit, mark wrong, forget; shows each lesson's `memory_events` history.

Iframes use `sandbox=""` without scripts.

## Build plan

Core loop works end to end by **2:30 PM**. Submissions close at **5:00 PM**.

| Time | P1: Generation | P2: Memory | P3: Frontend | P4: Data and demo |
|---|---|---|---|---|
| 10:45–11:30 | Repo, FastAPI skeleton, Claude client | Atlas sandbox, collections, indexes | Build screen layout, iframes | Seed users, teams, 15 starter lessons |
| 11:30–1:00 | Condense + generate A/B | Retrieval with team filter, re-rank | `/runs` wired to UI | Checklist auto-scorer |
| 1:00–2:30 | Reason tags → new lesson | Vote scoring, demote, retire, memory_events | Vote buttons, memory sidebar | Isolation unit test; memory-off toggle |
| 2:30–4:00 | Token savings, error handling | TTL + model-version expiry, admin edit/forget | Lesson admin page, deltas animation | Pre-run demo history so scores are warm |
| 4:00–5:00 | Freeze code | README "Built during the hackathon" | Polish | Rehearse demo twice, submit by 4:45 |

**Cut list if behind:** lesson admin page → curl only; Variant B explore logic → random lesson swap; reason-tag lessons → drop.

## Demo script (3 min)

1. **Hook (20 s):** "Prompts are team knowledge nobody governs. PromptForge remembers what works, forgets what doesn't, and proves it."
2. **Cold run (40 s):** memory off, "landing page for a coffee shop". Two plain sites, checklist ~2/6.
3. **Memory on (40 s):** same brief. Sidebar lists lessons used; ~5/6 with ~40% fewer prompt tokens. Vote live; scores move.
4. **Transfer (30 s):** "bakery site". Good first try using coffee lessons.
5. **Governance (40 s):** Team B, same brief, different style, zero shared lessons. Team A: forget top lesson, rerun, CTA disappears. Show `memory_events` trail.
6. **Close (10 s):** what we built today, repo link.

## Risks

| Risk | Mitigation |
|---|---|
| Generation is slow (2 × ~20 s) | Generate A and B in parallel; spinner; cached demo runs as fallback |
| Improvement looks random on stage | Warm scores with ~20 seeded votes; lead with checklist numbers |
| Wi-Fi or API outage | Pre-recorded 60 s video; cached run JSON |
| Judges call it basic RAG | Open with memory-off vs memory-on and the forget counterfactual |
| Generated HTML breaks the page | Sandboxed iframes, no scripts |
