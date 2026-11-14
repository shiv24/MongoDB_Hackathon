# One-minute PromptForge demo

Use Alice in the Admin console workspace. The server runs at http://localhost:8018.

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
