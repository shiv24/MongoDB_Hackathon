---
name: demo-prep
description: Prepare PromptForge's demo and submission - fixtures, the memory-change proof, fallback runs, the 1-minute video and the submission checklist. Use when asked to prepare, rehearse, record, or de-risk the demo or submission.
---

# Demo prep

Follow README "How we will prove it works". The demo task is still open; website generation is the leading candidate.

## Proof run
1. Seed: `python scripts/seed.py --reset` (one project with sources and decisions for team_a; team_b fixtures for isolation).
2. Run a fixed request. Show the sources and memories cited in the brief.
3. In a separate session, approve a specific lesson or supersede a decision.
4. Repeat the same request in a fresh session with the same model and starting revision.
5. Show the changed brief, the cited memory revision, and a **concrete, checkable** difference in the result.
6. Show that expired, superseded, unapproved and team_b memories are excluded.

Choose a lesson with an objective check (e.g. "signup page has a mobile layout", "uses the identity service"), not "looks better". A single before/after pair is demo evidence, not a benchmark; say so.

## Fallbacks
- Cache the run JSON in `cache/` (committed) and label it as a fixture/prerecorded fallback when used.
- Typed request if voice fails.

## Submission checklist (closes 5:00 PM Toronto)
- [ ] Using the Atlas Hackathon Sandbox
- [ ] Repo public
- [ ] 1-minute demo video plays; shows only work built today
- [ ] README status replaced with verified capabilities; original work vs third-party dependencies listed
- [ ] Every team member listed
- [ ] Concise project description submitted
