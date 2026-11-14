"""Add a separate event-page showcase. Never resets existing workspaces or lessons."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import get_db
from app.repo import context

def seed():
    db=get_db()
    project='team-events'
    for uid,name in [('events-alice','Alice'),('events-bob','Bob')]:
        db.users.update_one({'_id':uid},{'$setOnInsert':{'_id':uid,'name':name,'team_id':'events-team','project_ids':[project],'role':'publisher' if name=='Alice' else 'member'}},upsert=True)
    db.projects.update_one({'_id':project},{'$setOnInsert':{'_id':project,'team_id':'events-team','name':'Team events'}},upsert=True)
    s={'user_id':'events-alice','team_id':'events-team','project_ids':[project],'role':'publisher'}
    sources={
      'Pizza night': 'Build a friendly RSVP page for the team pizza night. Friday, November 20, 2026, 6–8 PM Eastern, at the office lounge. Free for teammates. Offer cheese, veggie and pepperoni pizza. Collect name, work email and pizza preference. Main action: Count me in. Show a friendly confirmation and a fully-booked state. Capacity: 30 people.',
      'Movie night': 'Build a friendly RSVP page for team movie night. Saturday, November 21, 2026, 7–10 PM Eastern, in the office screening room. Free entry; popcorn included. Collect name and work email. Main action: Save my seat. Show a friendly confirmation and a fully-booked state. Capacity: 20 people.',
    }
    existing={x['title'] for x in context.list_sources(s,project)}
    for title,text in sources.items():
        if title not in existing:context.add_source(s,project,title,text,'spec');print('Added '+title,flush=True)
    rules=[
      'Event pages must show the date, time, venue, price and remaining capacity clearly before the RSVP action.',
      'Keep RSVP simple: use visible field labels, keyboard-accessible controls, clear inline errors and a layout that works on phones. Never clear a completed form after an error.',
      'Only collect information needed for the event. Do not expose attendee email addresses publicly. A visual preview must label sample data and must not claim that RSVPs are actually stored.',
    ]
    existing={x['text'] for x in context.list_decisions(s,project)}
    for rule in rules:
        if rule not in existing:context.add_decision(s,project,rule);print('Added shared rule',flush=True)
    print('Event workspace ready; no learning lesson was pre-approved.',flush=True)
if __name__=='__main__':seed()
