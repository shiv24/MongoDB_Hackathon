---
name: demo-prep
description: Warm up PromptForge for the 3-minute demo by seeding votes, caching fallback runs, and walking the script. Use from ~2:30 PM onward, or when asked to prepare, rehearse, or de-risk the demo.
---

# Demo prep

## Warm-up (do before rehearsal)
1. `python scripts/seed.py --reset`: two teams, demo users (one admin, one expert), starter lessons.
2. Run ~20 seeded votes on Team A with the coffee-shop brief so scores are spread out, not all 0.5.
3. Cache the JSON for these runs in `cache/`: cold coffee (memory off), warm coffee (memory on), bakery, Team B coffee. They are the fallback if Wi-Fi or the API fails.
4. Check that the forget counterfactual works: find the top CTA lesson, forget it, rerun, and confirm the CTA disappears.

## Script (3:00)
Hook 0:20 → Cold run 0:40 → Memory on 0:40 → Transfer (bakery) 0:30 → Governance (Team B + forget) 0:40 → Close 0:10.
Full lines are in docs/DESIGN.md under "Demo script".

## Checklist
- [ ] Lead with checklist numbers and token savings, not taste
- [ ] Memory sidebar deltas are visible at projector size
- [ ] Mic tested on the venue laptop and Wi-Fi; mic permission granted in the browser beforehand
- [ ] 60 s backup video recorded
- [ ] Submitted by 4:45 PM
