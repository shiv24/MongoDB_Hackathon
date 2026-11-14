from datetime import timedelta
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import config
from app.agent import pipeline, llm
from app.repo import runs, lessons, agent_sessions
from app.db import now
from app.errors import Conflict, NotFound, NotLoggedIn
from app.routes.build import safe_html
from conftest import ALICE, BOB


def test_personal_provenance_does_not_leak_through_runs(db):
    r = runs.create(ALICE, 'signup', 'private', provenance=[{'text':'private guidance'}])
    with pytest.raises(NotFound): runs.get(BOB,r['_id'])
    assert runs.recent(BOB,'signup') == []


def test_expired_lesson_blocks_export_without_read_sweep(db):
    l=lessons.propose(ALICE,'signup','Use mobile layout','r','f',[],None,[])
    lessons.approve(ALICE,l['_id'],'project')
    db.lessons.update_one({'_id':l['_id']},{'$set':{'expires_at':now()-timedelta(days=1)}})
    r=runs.create(ALICE,'signup','x',status='draft',intent={'feature':'x'},brief={'objective':'x','preferences':[{'text':'mobile','sources':['L1']}],'open_questions':[]},provenance=[{'key':'L1','type':'lesson','id':l['_id'],'revision':1}])
    with pytest.raises(Conflict): pipeline.export(ALICE,r['_id'])
    assert db.lessons.find_one({'_id':l['_id']})['expires_at']<now()


def test_uncited_requirement_cannot_export(db):
    r=runs.create(ALICE,'signup','x',status='drafting',intent={'feature':'x'},provenance=[])
    pipeline.save_brief(ALICE,r['_id'],{'objective':'x','requirements':['Invented [S9]']})
    with pytest.raises(Conflict): pipeline.export(ALICE,r['_id'])


def test_token_rechecks_membership(db):
    db.users.insert_one({'_id':'alice','team_id':'team_a','project_ids':[],'role':'member'})
    _,token=agent_sessions.mint(ALICE,'signup')
    with pytest.raises(NotLoggedIn): agent_sessions.resolve(token)


def test_preview_removes_active_content():
    out=safe_html('<script>alert(1)</script><a href="https://evil">x</a><img onerror="alert(1)" src="https://evil"><iframe srcdoc="x"></iframe>')
    assert '<script' not in out and '<iframe' not in out and 'onerror' not in out and 'https://evil' not in out
    assert "default-src 'none'" in out


def test_direct_build_preview_and_cache(db,monkeypatch):
    from app.agent import retrieve
    monkeypatch.setattr(config,'OPENAI_API_KEY','test')
    db.users.insert_one({'_id':'alice','team_id':'team_a','project_ids':['signup'],'role':'publisher','name':'Alice'})
    db.projects.insert_one({'_id':'signup','team_id':'team_a','name':'Signup'})
    monkeypatch.setattr(retrieve,'gather',lambda *a:[])
    payload=llm.Draft(objective='Signup',requirements=['Build signup [U1]'],current_decisions=[],implementation_context=[],preferences=[],acceptance_checks=['Visible form'],blocking_questions=[],other_questions=[],assumptions=[],resolved_questions=[])
    monkeypatch.setattr(llm,'draft',lambda *a:(payload,{'input_tokens':10}))
    calls=[]
    monkeypatch.setattr(llm,'website',lambda *a:(calls.append(1) or llm.Website(html='<h1>Signup</h1>'),{'output_tokens':10}))
    c=TestClient(app);c.post('/api/login',json={'user_id':'alice'})
    r=c.post('/api/build',json={'project_id':'signup','request':'Build signup'})
    assert r.status_code==200,r.text
    rid=r.json()['_id']
    for _ in range(2):
        result=c.post(f'/api/build/{rid}/preview');assert result.status_code==200,result.text
        assert '<h1>Signup</h1>' in result.json()['artifact']['html']
    assert len(calls)==1
    assert c.get('/').status_code==200


def test_missing_openai_key_is_actionable(monkeypatch):
    monkeypatch.setattr(config,'OPENAI_API_KEY','')
    with pytest.raises(RuntimeError,match='OPENAI_API_KEY'):llm.propose('feedback')


def test_logout_revokes_agent_tokens(db):
    db.users.insert_one({'_id':'alice','team_id':'team_a','project_ids':['signup'],'role':'publisher','name':'Alice'})
    _,token=agent_sessions.mint(ALICE,'signup')
    c=TestClient(app);c.post('/api/login',json={'user_id':'alice'})
    c.post('/api/logout')
    with pytest.raises(NotLoggedIn):agent_sessions.resolve(token)


def test_transcription_requires_session(db):
    c=TestClient(app)
    assert c.post('/api/voice/transcribe',files={'audio':('a.webm',b'abc','audio/webm')}).status_code==401


def test_generation_rechecks_changes_after_provider_call(db,monkeypatch):
    from app.routes.build import preview
    from app.routes import build as route
    monkeypatch.setattr(route,'current',lambda r:ALICE)
    l=lessons.propose(ALICE,'signup','Use blue','r','f',[],None,[])
    lessons.approve(ALICE,l['_id'],'project')
    r=runs.create(ALICE,'signup','x',status='draft',brief_revision=1,intent={'feature':'x'},brief={'objective':'x','preferences':[{'text':'blue','sources':['L1']}],'open_questions':[]},provenance=[{'key':'L1','type':'lesson','id':l['_id'],'revision':1,'scope':'project','text':'blue'}])
    def generate(_):
        lessons.retire(ALICE,l['_id'])
        return llm.Website(html='<p>blue</p>'),{}
    monkeypatch.setattr(llm,'website',generate)
    with pytest.raises(Conflict):preview(None,r['_id'])
    after=runs.get(ALICE,r['_id'])
    assert not after.get('artifact') and after['generating'] is False
