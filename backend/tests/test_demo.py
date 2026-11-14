import pytest
from app.repo import demo, runs, context
from app.db import now
from app.errors import Conflict, NotFound


def template(db):
    db.projects.insert_one({'_id':demo.TEMPLATE,'team_id':'template-team','demo_template':True,'baseline_run_id':'baseline'})
    db.sources.insert_one({'_id':'chunk','source_id':'source','project_id':demo.TEMPLATE,'team_id':'template-team','revision':1,'scope':'project','text':'Use existing components','title':'Architecture'})
    db.runs.insert_one({'_id':'baseline','project_id':demo.TEMPLATE,'team_id':'template-team','request':'Add search','brief_revision':1,'status':'exported','brief':{'objective':'Search'},'artifact':{'html':'<h1>Users</h1>','brief_revision':1},'provenance':[{'key':'S1','type':'source','id':'source','chunk_id':'chunk','revision':1}]})


def session(user):
    return {**user,'user_id':user['_id']}


def test_repeated_demo_has_clean_memory_and_preserves_previous_round(db):
    template(db)
    first, before = demo.start()
    db.lessons.insert_one({'_id':'learned','team_id':first['team_id'],'project_id':before['project_id'],'status':'approved','text':'Purple'})
    second, fresh = demo.start()
    assert first['team_id'] != second['team_id']
    assert db.lessons.count_documents({'team_id':second['team_id']}) == 0
    assert db.lessons.count_documents({'_id':'learned'}) == 1
    assert before['artifact'] == fresh['artifact']
    assert before['provenance'][0]['id'] != fresh['provenance'][0]['id']
    assert runs.get(session(first),before['_id'])['_id'] == before['_id']
    with pytest.raises(NotFound): runs.get(session(second),before['_id'])
    assert db.runs.find_one({'_id':'baseline'})['provenance'][0]['id'] == 'source'


def test_fresh_demo_sources_available_before_index_sync(db,monkeypatch):
    template(db)
    user,run=demo.start()
    monkeypatch.setattr(context,'vector_search',lambda *a,**k: pytest.fail('Curated demo must not depend on index sync'))
    hits=context.search_sources(session(user),run['project_id'],[0.0])
    assert len(hits)==1 and hits[0]['text']=='Use existing components'


def test_missing_demo_template_changes_nothing(db):
    with pytest.raises(Conflict): demo.start()
    assert db.users.count_documents({}) == 0


def test_demo_endpoint_requires_login(db):
    from fastapi.testclient import TestClient
    from app.main import app
    assert TestClient(app).post('/api/demo/start').status_code == 401
