"""Add the named customer export example without resetting existing data.
Run with the local server on port 8018. Existing matching example records are reused.
"""
from pathlib import Path
import httpx

TITLE = 'Customer exports — product requirements'
RULES = ['Protect customer data: use explicit field allowlists for exports. Never include credentials, authentication tokens, payment details, private support notes or internal risk scores.', 'Enforce access on the server: derive workspace identity from the authenticated session and verify the required permission for every sensitive operation. Hidden UI controls and client-supplied tenant identifiers are not authorization.', 'Use a restrained, accessible visual system: light neutral content surfaces, dark navigation and green primary actions. Reserve strong colors for actions and status. This replaces the earlier requirement for every page to have a green background.', 'Design complete workflows: include loading, empty, success, permission-denied and failure states where relevant. Explain what happened and provide a clear next action; do not rely on color alone.', 'Preserve user intent: bulk operations must clearly state their scope, respect active filters, and request confirmation before consequential actions. Never silently limit an all-results action to the visible page.', 'Reuse documented services and conventions. If repository details are missing, identify integration work rather than inventing file paths, API names or claims of working functionality.', 'Keep audits minimal: record actor, workspace, action, outcome and timestamp for sensitive operations. Do not log secrets or entire customer records.']
with httpx.Client(base_url='http://localhost:8018/api', timeout=90) as client:
    client.post('/login', json={'user_id':'alice'}).raise_for_status()
    context = client.get('/projects/lumen-signup/context').json()
    if not any(s['title'] == TITLE for s in context['sources']):
        response = client.post('/projects/lumen-signup/sources', json={
            'title': TITLE, 'text': (Path(__file__).resolve().parents[1]/'docs/CUSTOMER_EXPORTS.md').read_text(), 'kind':'spec'})
        response.raise_for_status()
        print('Added product requirements')
    for rule in RULES:
        if not any(d['text'] == rule and d['status'] == 'current' for d in context['decisions']):
            client.post('/projects/lumen-signup/decisions', json={'text':rule}).raise_for_status()
            print('Added project rule')
print('Context ready. Allow a moment for Atlas indexing before generating.')
