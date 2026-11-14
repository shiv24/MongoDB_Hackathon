---
name: atlas-setup
description: Create or verify PromptForge's MongoDB Atlas collections, validators, Vector Search indexes and TTL index in the hackathon sandbox. Use when setting up Atlas, changing the schema or indexes, or debugging $vectorSearch returning nothing.
---

# Atlas setup

Database: `promptforge` (from `MONGODB_DB`). Everything lives in the **hackathon Atlas Sandbox project** from the invite email; finalists must use it. Never use a personal cluster.

## Steps
1. Confirm `.env` has `MONGODB_URI`, `MONGODB_DB` and `EMBED_DIMS`.
2. Run `python scripts/setup_atlas.py` (idempotent). It creates the collections in docs/DESIGN.md "Data model" and:
   - Vector Search indexes (`numDimensions: EMBED_DIMS`, cosine):
     - `sources_vector`, with filters `team_id`, `project_id`
     - `decisions_vector`, with filters `team_id`, `project_id`, `status`
     - `lessons_vector`, with filters `team_id`, `project_id`, `owner_id`, `scope`, `status`
   - TTL index on `lessons.purge_at` (`expireAfterSeconds: 0`). **Not** on `expires_at`.
   - `lessons.{team_id, expires_at}` for the expiry sweep, plus the regular indexes listed in DESIGN.md
   - a JSON Schema validator on `memory_events`
3. Vector Search indexes build asynchronously. Wait for `READY` before querying.
4. Seed with `python scripts/seed.py --reset` (fixtures in `scripts/data/fixtures.json`; embeds with Voyage).
5. Verify with `pytest backend/tests/test_isolation.py`, which runs live `$vectorSearch` checks for isolation and exclusion of proposed, expired, retired, superseded and personal memory.

## Gotchas
- Every field used in a `$vectorSearch` filter must be declared as a `filter` field in that index, or the query errors. `repo/scope.py` filters on `team_id`, `status`, `scope`, `project_id`, `owner_id`.
- A `numDimensions` mismatch with the embedding model makes searches return nothing, with no error.
- TTL deletes run in a background job with no hook into our code. They are only for the final purge; the app's sweep logs `expired` first.
- Free and shared tiers cap the number of search indexes. We need three, so check the sandbox allows that. If not, merge decisions and lessons into one `memory` collection with a `kind` filter.
- Insert-only access on `memory_events` is an Atlas custom role. If the sandbox tier doesn't allow it, say so in the README.
