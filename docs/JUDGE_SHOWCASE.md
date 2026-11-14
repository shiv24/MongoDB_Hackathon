# Judge showcase: same request, visibly better instructions

## Setup
Run `python scripts/seed_software_showcase.py` once with Atlas and Voyage configured. Open the app as Alice in the Admin console workspace. The shared brain contains sample project history, shared components and engineering decisions. Keep the same generation-model settings for both runs.

## Visual walkthrough
1. Click Use an example request: “Add search to the users table. Show sample results for a search for Alex.” Create prompt → Preview website → **Keep as before**.
2. Click Use example feedback. It asks for a pale amber banner above active search results, with query, matching count and Clear search button. Click Suggest a lesson, review it, select **This project**, and approve.
3. Click **Use the same request again**, then Create prompt. Point to **Learned guidance used** and its approved lesson. Click Preview website.
4. Click **Compare before & after**. Show the same user request and model, the actual two saved outputs, and the visible search-summary change.

Narration: “We didn't rewrite the request or manually improve the prompt. We taught the shared brain one preference. It supplied the new instructions to the same model.”

Optional closing: switch to Bob and request Orders search to demonstrate project-wide reuse in a fresh session.

The HTML preview is inert. Do not claim the buttons work or the backend exists. Model variation can affect other visual details; the cited lesson and matching instruction support the intended change, while a single pair is not a controlled benchmark. Check that the amber banner actually appears before presenting. A rehearsal leaves the lesson approved; do not present repeated learning as new. Pinning stores a run ID per demo identity in this browser; authorization is still checked when loading it. Old previews are historical snapshots, not current approved instructions.
