"""Add a separate software-form showcase. Never resets existing workspaces or lessons."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import get_db
from app.repo import context

def seed():
    db=get_db()
    project='product-forms'
    for uid,name in [('forms-alice','Alice'),('forms-bob','Bob')]:
        db.users.update_one({'_id':uid},{'$setOnInsert':{'_id':uid,'name':name,'team_id':'forms-team','project_ids':[project],'role':'publisher' if name=='Alice' else 'member'}},upsert=True)
    db.projects.update_one({'_id':project},{'$setOnInsert':{'_id':project,'team_id':'forms-team','name':'Product workspace'}},upsert=True)
    s={'user_id':'forms-alice','team_id':'forms-team','project_ids':[project],'role':'publisher'}
    sources={
      'Signup form': 'Build the signup form for a team collaboration app. Collect full name, work email and password. Require acceptance of terms. The primary action is Create account. On success show a welcome message and a Create workspace next step. Use existing authentication services when implementation details are available; do not invent API names or store passwords in the frontend.',
      'Billing form': 'Build the billing-details form for a team collaboration app. Workspace administrators can update company name, billing email, country and postal code. The primary action is Save billing details. Show the current plan and a success confirmation. Ordinary members see read-only details. Do not collect credit-card numbers in this form.',
    }
    existing={x['title'] for x in context.list_sources(s,project)}
    for title,text in sources.items():
        if title not in existing:context.add_source(s,project,title,text,'spec');print('Added '+title,flush=True)
    rules=[
      'Use visible field labels, keyboard-accessible controls and a responsive layout. Keep the main action clear and write interface copy in plain language.',
      'Enforce authorization and validate data on the server. Reuse existing project services when documented; do not invent file paths, endpoints or claims of working integrations.',
      'Use sample data for generated visual previews. Clearly distinguish a visual prototype from working authentication, saved data or backend services.',
    ]
    existing={x['text'] for x in context.list_decisions(s,project)}
    for rule in rules:
        if rule not in existing:context.add_decision(s,project,rule);print('Added shared rule',flush=True)
    print('Software workspace ready; no learning lesson was pre-approved.',flush=True)
if __name__=='__main__':seed()
