---
name: atlas-setup
description: Create or verify PromptForge's MongoDB Atlas collections, validators, Vector Search index, and TTL index in the hackathon sandbox. Use when setting up Atlas, changing the schema or indexes, or debugging $vectorSearch returning nothing.
---

# Atlas setup

Database: `promptforge` (from `MONGODB_DB`). Everything lives in the **hackathon sandbox project** from the invite email. Never use a personal cluster.

## Steps
1. Confirm `.env` has `MONGODB_URI`, `MONGODB_DB` and `EMBED_DIMS`.
2. Run `python scripts/setup_atlas.py`. It is idempotent and creates:
   - collections `users`, `lessons`, `runs`, `votes`, `memory_events`
   - `memory_events` JSON Schema validator
   - regular indexes: `users.team_id`, `lessons.{team_id, score}`, `runs.{team_id, created_at}`, unique `votes.{run_id, user_id}`, `memory_events.{lesson_id, at}`
   - TTL index on `lessons.expires_at` (`expireAfterSeconds: 0`)
   - Vector Search index `lessons_vector` (see docs/DESIGN.md)
3. Vector Search indexes build asynchronously. Wait for status `READY` before querying.

## Gotchas
- `numDimensions` must equal the embedding model's output (voyage-3 → 1024). A mismatch makes searches return nothing, with no error.
- Filter fields (`team_id`, `status`, `category`) must be declared in the index, or `$vectorSearch` rejects the filter.
- Insert-only access for `memory_events` is configured as an Atlas database user role in the UI. Note it in the README if it is not done by script.
