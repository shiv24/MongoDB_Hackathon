# Judge showcase: signup → billing

Run `python scripts/seed_software_showcase.py` once with Atlas and Voyage configured. This adds a separate Product workspace, Alice and Bob demo identities, two short software specs and three shared rules. It does not reset other workspaces or pre-approve the learning lesson. Identity switching is simulated for the hackathon.

## 90-second walkthrough
1. **Alice builds a signup prompt.** Select Alice, click Use an example request, then Create prompt. “The brain starts with our requirements and engineering rules.”
2. **Teach once.** Click Use example feedback, then Suggest a lesson. The feedback says to preserve entered values after validation errors, show an error summary and focus the first invalid field. Review the lesson, choose **This project**, then Approve for future prompts.
3. **Bob starts fresh.** Switch to Bob, click the example request for a billing form, and create the prompt. Bob never mentions error handling.
4. **Show the transfer.** Point to Learned guidance used and Alice's approval. “Different developer, different feature, fresh session. Bob benefits from what Alice learned.”

Close: “Your next prompt benefits from what your teammates already figured out.”

Keep website generation optional. A preview is not a functioning backend. The evidence is the cited lesson and its transfer, not a guarantee the model would never independently suggest similar guidance. Allow Atlas indexing time after approval. If rehearsed, disclose already-approved memory instead of pretending it was newly learned.
