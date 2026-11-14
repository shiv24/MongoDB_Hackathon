---
name: memory-loop
description: The PromptForge agent loop (retrieve, condense, generate A/B, checklist score, vote, update memory) with its exact formulas and thresholds. Use when implementing or changing anything in backend/app/agent/ or lesson scoring.
---

# Memory loop

Code: `backend/app/agent/`. One module per step. Keep the numbers below in `backend/app/config.py`, not inline.

| Step | Module | Rule |
|---|---|---|
| Retrieve | `retrieve.py` | `$vectorSearch` limit 8, filter `{team_id, status:"active"}`; re-rank `0.6·sim + 0.4·score` |
| Condense | `condense.py` | Claude: merge into one prompt < 150 words, drop duplicates and contradictions, keep imperatives; record `tokens_raw`, `tokens_condensed` |
| Generate | `generate.py` | A = top lessons (exploit). B = swap in 1–2 lower-ranked, demoted or new lessons (explore). Run both in parallel. Output one self-contained HTML file, no `<script>` |
| Score | `score.py` | 0–6 checklist: hero heading, one primary CTA, viewport meta, ≤ 4 colors, img alt text, nav |
| Update | `memory.py` | winners `wins += w`, losers `losses += w`; `score = (wins+1)/(wins+losses+2)` |

## Lifecycle thresholds
- `score < 0.35` after ≥ 4 votes → `demoted` (Variant B only)
- `score < 0.2` after ≥ 6 votes → `retired` (never retrieved)
- `expires_at = last_win + 30 days`; a win pushes it forward
- `model_version != current` → set to `demoted` for re-testing
- Reason tags on the winner → candidate lesson; skip it if any existing lesson has similarity > 0.92

## Rule
Every status or score change inserts a `memory_events` row (`event`, `actor`, `cause`, `before`, `after`, `at`). If a change is not logged, the audit trail breaks.

Memory-off mode (`memory: false`) skips retrieve and condense and uses a bare brief prompt. It is the control group for the demo.
