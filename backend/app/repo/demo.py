"""Repeatable rehearsals: copy an explicitly prepared sample template, never reset team data."""
from copy import deepcopy
from app.db import get_db, new_id, now
from app.errors import Conflict

TEMPLATE = 'promptforge-demo-template'


def start():
    db = get_db()
    template = db.projects.find_one({'_id': TEMPLATE, 'demo_template': True})
    baseline = db.runs.find_one({'_id': (template or {}).get('baseline_run_id'), 'project_id': TEMPLATE})
    if not baseline or not baseline.get('artifact'):
        raise Conflict('Demo template is not ready. Run python scripts/prepare_demo.py first.')
    if any(e['type'] == 'lesson' for e in baseline.get('provenance', [])):
        raise Conflict('Demo template must not contain learned preferences.')
    token = new_id()
    project_id, user_id, team_id = 'demo-' + token, 'demo-alice-' + token, 'demo-team-' + token
    user = {'_id':user_id, 'name':'Alice', 'team_id':team_id, 'project_ids':[project_id], 'role':'publisher'}
    mappings = {}
    collections = {}
    for name in ('sources', 'decisions'):
        docs = list(db[name].find({'project_id':TEMPLATE, 'team_id':template['team_id']}))
        for doc in docs:
            for field in ('_id', 'source_id'):
                if doc.get(field): mappings.setdefault(doc[field], new_id())
        collections[name] = docs
    for name, docs in collections.items():
        for doc in docs:
            doc['_id'] = mappings[doc['_id']]
            if 'source_id' in doc: doc['source_id'] = mappings[doc['source_id']]
            doc.update(team_id=team_id, project_id=project_id, owner_id=user_id, added_by=user_id)
        if docs: db[name].insert_many(docs)
    run = deepcopy(baseline)
    run_id = new_id()
    for entry in run['provenance']:
        if entry['type'] == 'lesson':
            raise Conflict('Demo template must not contain learned preferences.')
        if entry['type'] == 'user': entry['id'] = run_id
        else: entry['id'] = mappings[entry['id']]
        if entry.get('chunk_id'): entry['chunk_id'] = mappings[entry['chunk_id']]
        if entry.get('owner_id'): entry['owner_id'] = user_id
    run.update(_id=run_id, user_id=user_id, team_id=team_id, project_id=project_id,
               created_at=now(), generating=False, demo_baseline=True)
    db.users.insert_one(user)
    db.projects.insert_one({'_id':project_id, 'name':'Demo · Admin console', 'team_id':team_id, 'demo':True})
    db.runs.insert_one(run)
    return user, run
