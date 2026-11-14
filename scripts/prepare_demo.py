"""Load a reusable, lesson-free prepared starting preview. Additive; never resets team data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.db import get_db, new_id
from app.repo.demo import TEMPLATE
from seed_software_showcase import seed

seed()
db = get_db()
team = 'demo-template-team'
user = 'demo-template-alice'
s = {'user_id':user,'name':'Alice','team_id':team,'project_ids':[TEMPLATE],'role':'publisher'}
db.users.update_one({'_id':user},{'$setOnInsert':{'_id':user,'name':'Alice','team_id':team,'project_ids':[TEMPLATE],'role':'publisher'}},upsert=True)
db.projects.update_one({'_id':TEMPLATE},{'$setOnInsert':{'_id':TEMPLATE,'team_id':team,'name':'Sample admin console','demo_template':True}},upsert=True)
template = db.projects.find_one({'_id':TEMPLATE})
if template.get('baseline_run_id') and db.runs.find_one({'_id':template['baseline_run_id'],'artifact':{'$exists':True}}):
    print('Demo template already ready.');sys.exit(0)
# These are the four sample documents created by seed_software_showcase, not user uploads.
for title in ['Project overview — existing admin console','Architecture notes — established conventions','Previous sprint — search performance decision','Current tickets — users and orders search']:
    if not db.sources.find_one({'project_id':TEMPLATE,'title':title}):
        for source in db.sources.find({'project_id':'admin-console','title':title,'added_by':'console-alice'}):
            source.update(_id=new_id(),source_id=new_id(),team_id=team,project_id=TEMPLATE,scope='project',owner_id=user,added_by=user)
            db.sources.insert_one(source)
entries=[]
for i, source in enumerate(db.sources.find({'project_id':TEMPLATE}),1):
    entries.append({'key':f'S{i}','type':'source','id':source['source_id'],'chunk_id':source['_id'],'revision':source['revision'],'title':source['title'],'scope':'project','text':source['text']})
from app.repo import runs
request='Add search to the users table. Show sample results for a search for Alex.'
run=runs.create(s,TEMPLATE,request,status='drafting',intent={'feature':request},provenance=entries,author={'kind':'openai'})
entries.append({'key':'U1','type':'user','id':run['_id'],'revision':1,'text':request})
runs.update(s,run['_id'],{'provenance':entries})
import json
fixture=json.loads((Path(__file__).parent/'data'/'demo_baseline.json').read_text())
runs.update(s,run['_id'],{'brief':fixture['brief'],'brief_revision':1,'status':'draft',
                        'artifact':{**fixture['artifact'],'brief_revision':1},'model':'prepared-demo'})
db.projects.update_one({'_id':TEMPLATE},{'$set':{'baseline_run_id':run['_id']}})
print('Reusable prepared demo template ready:',run['_id'],flush=True)
