# Judge showcase: the admin dashboard your team has maintained for months

Run `python scripts/seed_software_showcase.py`. It adds an isolated Admin console workspace, Alice and Bob demo identities, four short sample project documents and three established engineering rules. Documents represent accumulated project history; do not claim they came from actual months of production usage. No pagination lesson is pre-approved.

## 90-second story
1. **Existing project:** briefly open the brain. Show architecture notes, the earlier search-performance decision and the current tickets. “Our team has been maintaining this dashboard. The brain holds the decisions we would normally have to explain again.”
2. **Alice:** Use an example request → Create prompt. The request is simply “Add search to the users table.” Point to server-side search, existing shared components, 300 ms debounce, URL state and stale-request handling. None was in her sentence.
3. **The bug:** Use example feedback. “We tested from page 8. Changing search looked broken because pagination stayed on page 8.” Suggest a lesson, choose This project, then approve. The lesson requires resetting pagination and a regression test from a later page.
4. **Bob:** switch sessions, use the Orders-table example and create the prompt. Show Learned guidance used and Alice's attribution. “Bob didn't see that bug. His prompt already tells his agent how to avoid it.”

Close: “Months of team context, plus yesterday's lesson, in the next prompt.”

Keep the website preview optional. The proof is project-specific instructions and cited transfer of approved learning. Inspect any already-approved rehearsal lessons before presenting. Allow indexing time after approval. A conventional model could independently suggest resetting pagination; demonstrate the actual citation and provenance rather than claiming exclusivity.
