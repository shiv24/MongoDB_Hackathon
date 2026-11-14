---
name: governance-guardrails
description: PromptForge's team-isolation, audit, and vote-integrity invariants. Use before writing or reviewing any route, query, or admin action that touches lessons, votes, or memory_events.
---

# Governance guardrails

Check each change against these. They map to the Track 2 judging questions.

## Isolation
- [ ] `team_id` is read from `request.session`, never from the body, query string or path.
- [ ] The query goes through `backend/app/repo/lessons.py`. No other module touches `db.lessons`.
- [ ] `$vectorSearch` puts `team_id` in `filter` (a pre-filter), not in a later `$match`.
- [ ] `backend/tests/test_isolation.py` still passes: a Team B query returns zero Team A ids.

## Correct and forget
- Mark wrong → `status: retired`, event `retired`, `cause: admin`.
- Edit → new text + re-embed, event `corrected` with old text in `before`.
- Forget → hard delete the lesson, event `forgotten` **without** the text.
- Admin endpoints check `role == "admin"` from the session user.

## Audit and votes
- [ ] `memory_events` gets inserts only: no update or delete anywhere in the code.
- [ ] Votes copy `weight` from `users.vote_weight` when cast.
- [ ] Duplicate votes are rejected by the unique `{run_id, user_id}` index. Handle `DuplicateKeyError` → 409.

## Rendering
- [ ] Generated HTML appears only in `<iframe sandbox="" srcdoc=...>`.
