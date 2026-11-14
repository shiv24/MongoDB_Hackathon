# Quick visual demo

Open PromptForge as Alice in the Admin console workspace.

1. **Build:** use the example request and click Build preview. The app creates a grounded prompt and sends it to the preview model automatically.
2. **Refine:** type “When search is active, show a pale amber banner above the table with the query, result count and a Clear search button.” Choose This project under Who should remember this?, then click Save feedback & rebuild. This explicitly approves the text at the chosen scope.
3. **Compare:** the app reruns the same request and opens the actual before-and-after outputs. Point to the amber banner and the newly cited lesson.

Say: “Same request. Same model. Our team’s feedback changed the instructions.”

The generated prompt and evidence remain under View the prompt and what shaped it. Preview HTML is illustrative, not a working backend. Model variation may change other styling. If the new lesson is not cited, the comparison explicitly says so: allow indexing time and rebuild before claiming the change came from memory. Rehearsals leave approved memory; use the saved before/after pair or disclose existing lessons.

Loading shows two real stages: writing the grounded prompt, then generating the visual preview. Wait for completion; the elapsed timer is not a completion estimate. The comparison opens automatically after a successful rebuild.
