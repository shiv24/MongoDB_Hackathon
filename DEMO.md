# One-minute PromptForge demo

Use Alice in the Admin console workspace. Follow [local setup](README.md#run-locally), then open http://localhost:8000 (or the port you started).

## Portable walkthrough

1. Prepare the template with `python scripts/prepare_demo.py` after Atlas index setup.
2. Start the server and click **Start fresh demo**. Identify the starting preview as saved; it is copied from a committed fixture without a model call.
3. Click **Use example feedback**, select **This project**, then **Save feedback & rebuild**. This explicitly approves the text and generates a new brief and preview live.
4. Compare the action buttons and inspect the cited approved lesson. Same request and model configuration do not guarantee identical layout elsewhere.
5. Use **Team workspace** to return to normal work, or **Start fresh demo** for another isolated round. Existing data is preserved.

Source embeddings/reranking and live rebuilds need configured providers. Each demo round creates records that remain in Atlas; it does not wipe earlier rounds. Normal workspace requests use Vector Search; the isolated demo reads its copied curated sources directly and reranks them to avoid index lag.

## Historical rehearsal links

The links below refer to records in the original rehearsal database on port 8018. They are not available automatically in a fresh database. Use the portable walkthrough above for a new installation.

[Open the tested, saved comparison (backup)](http://localhost:8018/#run=ccb9a762457f41b39026a2bd53fe632c&before=3134704de537471fb41c6dd666372c45).

[Start the live demo here](http://localhost:8018/#run=3134704de537471fb41c6dd666372c45). The original preview is already generated. Click **Use example feedback**, keep **This project**, then **Save feedback & rebuild**. The rehearsal purple lesson has been retired so this starts with no active purple rule from that rehearsal.

For the saved backup comparison:

1. Point to the original users table on the left.
2. Read the saved guidance: use purple action buttons with white text.
3. Point to the purple Clear search button on the right. Same request, same model, a new cited project lesson in the prompt.

Say: “Our team already has months of project decisions. PromptForge turns a short request into an informed prompt. When we teach it a preference, that approved guidance becomes shared memory and steers the next result.”



The saved comparison opens without another model call. Live generation takes two provider calls, with progress shown. Saved rehearsal previews are static HTML/CSS. Newly generated previews can include sandboxed client-side interactions over sample data; neither is a connected backend application. Generated layouts can also vary between runs; point to the cited lesson and the requested colour change rather than claiming every difference was caused by memory.

## Verified

- Real Atlas/Voyage/OpenAI flow: request → brief → preview → project feedback approval → new brief → new preview.
- The new approved lesson is present in provenance and purple appears in the brief and generated button CSS.
- Same request and generation model for both saved runs; visually inspected in Chrome.
- 49 offline tests pass; 3 Atlas integration tests skipped in the offline suite.

Freshly approved feedback is explicitly included in its immediate rebuild after scope/status checks, so it does not depend on vector-index synchronization. Other requests continue to retrieve applicable approved memory normally.

## Merged interactive preview check

[Open the tested interactive users table](http://localhost:8018/#run=02aaa2ccc3514f31ae9eb9b94d4762ae). Type Alex to see four matches and page 1 of 1, then Clear search to return to the full sample dataset. This is a separate verification run, not the original before/after comparison. Sandbox URL updates are intentionally ignored; this prototype does not change the browser URL.

## Repeat the demo reliably

Open http://localhost:8018 and click **Start fresh demo** in the header. Each click makes an isolated sample team and project with four sources, no approved lessons, and the same saved starting preview. No original team data or earlier rounds are deleted.

1. Show the starting preview (explicitly labeled as saved).
2. Click **Use example feedback**, keep **This project**, then **Save feedback & rebuild**.
3. Show the generated purple buttons and the cited new guidance in the comparison.
4. Close the comparison and click **Start fresh demo** for the next audience.

**Team workspace** returns to the original shared workspace. The demo uses direct scoped reads of its four curated sample sources plus reranking so it does not depend on indexing new copies. Normal workspaces continue using Atlas Vector Search. The new brief and after-preview are generated live; their timing and layouts can vary.

On a new database, run `python scripts/setup_atlas.py`, then `python scripts/prepare_demo.py` once. Preparation creates the sample context and loads the committed prepared starting preview. Subsequent preparation calls reuse it. Fresh-demo resets do not call a model.
