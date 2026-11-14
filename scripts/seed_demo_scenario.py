"""Add the named synthetic demo scenario without resetting existing data.
Run with the local server on port 8018. Existing matching demo records are reused.
"""
from pathlib import Path
import httpx

TITLE = 'DEMO · Northstar secure customer exports'
RULES = [
    'DEMO Northstar exports: export only customer name, company, email, account status and created date. Never export secrets, payment details, private notes or internal risk scores.',
    'DEMO Northstar exports: enforce workspace isolation and administrator permission on the server; export all rows matching the active filters in the authorized workspace.',
    'DEMO Northstar exports: use ivory content surfaces and forest-green navigation with restrained green actions. For this synthetic demo only, this decision supersedes the older all-green-background source styling.',
]
with httpx.Client(base_url='http://localhost:8018/api', timeout=90) as client:
    client.post('/login', json={'user_id':'alice'}).raise_for_status()
    context = client.get('/projects/lumen-signup/context').json()
    if not any(s['title'] == TITLE for s in context['sources']):
        response = client.post('/projects/lumen-signup/sources', json={
            'title': TITLE, 'text': (Path(__file__).resolve().parents[1]/'docs/DEMO_SCENARIO.md').read_text(), 'kind':'demo'})
        response.raise_for_status()
        print('Added synthetic demo source')
    for rule in RULES:
        if not any(d['text'] == rule and d['status'] == 'current' for d in context['decisions']):
            client.post('/projects/lumen-signup/decisions', json={'text':rule}).raise_for_status()
            print('Added demo decision')
print('Demo ready. Allow a moment for Atlas indexing before generating.')
