# Judge showcase: pizza night → movie night

## Setup
Run `python scripts/seed_events_showcase.py` once with Atlas and Voyage configured. It creates a separate Team events workspace, two demo identities, two short specs, and three shared rules. It does not pre-approve the calendar lesson or reset other data. Start the server and open the app. Identity switching is simulated for the hackathon.

## 90-second presentation
1. **Alice:** click Use an example request, then Create prompt. “Alice is making a pizza-night RSVP page. The brain knows the date, venue, menu and shared design rules.”
2. **Teach:** click Use example feedback. “We forgot something useful: add every event to your calendar after RSVP.” Click Suggest a lesson, review it, choose **This project**, then Approve for future prompts. Approval does not rewrite the existing prompt.
3. **Bob:** switch to Bob. Click Use an example request, then Create prompt. “Bob is making a movie-night page. Different teammate. Fresh session. He never mentioned a calendar.”
4. Point to **Learned guidance used**, the Add to calendar instruction and Alice's approval. Open the shared brain to show the durable project lesson.

Close: “Teach it once. Your whole team starts smarter next time.”

Skip website generation in a tight presentation; it is optional visual proof, not the product. Preview HTML is inert and does not store RSVPs or create working calendar downloads. If already rehearsed, show the approved lesson honestly as existing memory rather than pretending it was just learned. Allow a moment for Atlas indexing after approval.
