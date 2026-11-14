"""Add a separate software-form showcase. Never resets existing workspaces or lessons."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import get_db
from app.repo import context

def seed():
    db=get_db()
    project='admin-console'
    for uid,name in [('console-alice','Alice'),('console-bob','Bob')]:
        db.users.update_one({'_id':uid},{'$setOnInsert':{'_id':uid,'name':name,'team_id':'console-team','project_ids':[project],'role':'publisher' if name=='Alice' else 'member'}},upsert=True)
    db.projects.update_one({'_id':project},{'$setOnInsert':{'_id':project,'team_id':'console-team','name':'Admin console'}},upsert=True)
    s={'user_id':'console-alice','team_id':'console-team','project_ids':[project],'role':'publisher'}
    sources={
      'Project overview — existing admin console': 'Sample project context representing a team maintaining an admin dashboard for several months. The app already has Users and Orders tables. Both use server-side pagination, 25 rows per page. New work should extend existing tables, not rebuild the app. Users search matches name or email. Orders search matches order number or customer name. Preserve the current sort and unrelated filters.',
      'Architecture notes — established conventions': 'Sample architecture snapshot: React frontend and an existing REST backend. All frontend requests go through the shared apiClient, which attaches the session and normalizes errors. Use the shared DataTable, SearchInput and EmptyState components. Search belongs on the server because the browser has only one page of results. Endpoint paths and file locations are not provided: inspect the repository before naming or editing them.',
      'Previous sprint — search performance decision': 'Sample retained team decision: use a 300 ms debounce on table search. Cancel superseded requests or ignore their results so a slow old response cannot overwrite a newer query. Search state should be represented in URL parameters so a teammate can share the same view. Do not issue a request for every keystroke.',
      'Current tickets — users and orders search': 'Add a search input above the existing Users table, matching names or emails. A second ticket adds search to the existing Orders table, matching order numbers or customer names. Both need loading, no-results and request-error states, and a clear-search action. Test the actual table behavior rather than only whether the input appears. This is a sample backlog for the showcase, not a connected production repository.',
    }
    existing={x['title'] for x in context.list_sources(s,project)}
    for title,text in sources.items():
        if title not in existing:context.add_source(s,project,title,text,'spec');print('Added '+title,flush=True)
    rules=[
      'Extend existing components and API conventions. Reuse apiClient, DataTable, SearchInput and EmptyState where the repository confirms them. Inspect actual files and endpoint contracts; do not invent paths.',
      'Search paginated tables on the server. The browser holds only one page, so filtering loaded rows does not search the complete dataset.',
      'Debounce table searches by 300 ms and prevent stale responses from overwriting newer results. Keep search state shareable through the URL.',
    ]
    existing={x['text'] for x in context.list_decisions(s,project)}
    for rule in rules:
        if rule not in existing:context.add_decision(s,project,rule);print('Added shared rule',flush=True)
    print('Software workspace ready; no learning lesson was pre-approved.',flush=True)
if __name__=='__main__':seed()
