# One-minute PromptForge demo

Use Alice in the Admin console workspace. The server runs at http://localhost:8018.

[Open the tested, saved comparison](http://localhost:8018/#run=ccb9a762457f41b39026a2bd53fe632c&before=3134704de537471fb41c6dd666372c45).

1. Point to the original users table on the left.
2. Read the saved guidance: use purple action buttons with white text.
3. Point to the purple Clear search button on the right. Same request, same model, a new cited project lesson in the prompt.

Say: “Our team already has months of project decisions. PromptForge turns a short request into an informed prompt. When we teach it a preference, that approved guidance becomes shared memory and steers the next result.”

For a live run: close the comparison, enter feedback, choose **This project**, and press **Save feedback & rebuild**. It saves your exact feedback and opens the comparison automatically. The purple lesson is already saved from rehearsal; choose a different non-conflicting change, such as “Use Georgia for table headings in this project,” to demonstrate new learning. Explicitly approve any proposed replacement if you use the advanced lesson flow.

The saved comparison opens without another model call. Live generation takes two provider calls, with progress shown. Previews are inert HTML/CSS with sample data, not functioning backend applications. Generated layouts can also vary between runs; point to the cited lesson and the requested colour change rather than claiming every difference was caused by memory.

## Verified

- Real Atlas/Voyage/OpenAI flow: request → brief → preview → project feedback approval → new brief → new preview.
- The new approved lesson is present in provenance and purple appears in the brief and generated button CSS.
- Same request and generation model for both saved runs; visually inspected in Chrome.
- 44 offline tests pass; 3 Atlas integration tests skipped in the offline suite.

Freshly approved feedback is explicitly included in its immediate rebuild after scope/status checks, so it does not depend on vector-index synchronization. Other requests continue to retrieve applicable approved memory normally.
