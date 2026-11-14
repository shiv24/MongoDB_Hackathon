"""Direct typed workflow; generated previews run in an isolated iframe."""
from copy import deepcopy

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from app.agent import pipeline, llm, brief as brief_mod
from app.repo import runs, lessons, scope
from app.db import get_db, now
from app.session import current
from app.errors import Conflict
router = APIRouter(prefix='/build')
ARTIFACT_VERSION = 2

GROUNDED_SECTIONS = {
    'requirements': {'S', 'D', 'L', 'U'},
    'current_decisions': {'D'},
    'implementation_context': {'S', 'D'},
    'preferences': {'L'},
}

class RequestIn(BaseModel):
    project_id: str
    request: str = Field(min_length=1, max_length=8000)
    clarification: str = Field(default='', max_length=8000)
    lesson_ids: list[str] = Field(default_factory=list, max_length=5)


def include_selected_lessons(session, project_id, entries, lesson_ids):
    """Include explicitly approved feedback even before the vector index catches up."""
    scope.require_project(session, project_id)
    result = list(entries)
    for lesson_id in dict.fromkeys(lesson_ids):
        lesson = lessons.current_state(session, lesson_id)
        if (not lesson or lesson['status'] != 'approved' or
                (lesson['scope'] == 'project' and lesson['project_id'] != project_id)):
            raise Conflict('This feedback is no longer approved or available for this project.')
        result = [entry for entry in result if not (entry['type'] == 'lesson' and entry['id'] == lesson_id)]
        index = max([int(e['key'][1:]) for e in result if e['type'] == 'lesson'] or [0]) + 1
        result.append({'key': f'L{index}', 'type': 'lesson', 'id': lesson_id,
                       'revision': lesson['revision'], 'scope': lesson['scope'],
                       'owner_id': lesson['owner_id'], 'approved_by': lesson.get('approved_by'),
                       'text': lesson['text'], 'selection': 'explicit_feedback'})
    return result


def ground_direct_payload(value, valid_keys: set[str]) -> dict:
    """Keep governed claims cited; turn uncited model additions into explicit assumptions."""
    payload = value.model_dump()
    assumptions = list(payload.get('assumptions') or [])
    for section, prefixes in GROUNDED_SECTIONS.items():
        grounded = []
        for text in payload.get(section) or []:
            text = brief_mod.normalize_citations(text)
            keys = brief_mod.CITE.findall(text)
            allowed = {key for key in keys if key in valid_keys and key[0] in prefixes}
            if allowed:
                grounded.append(brief_mod.CITE.sub(
                    lambda match: match.group(0) if match.group(1) in allowed else '', text).strip())
            else:
                assumption = brief_mod.CITE.sub('', text).strip()
                if assumption:
                    assumptions.append(assumption)
        payload[section] = grounded
    payload['assumptions'] = list(dict.fromkeys(assumptions))
    return payload


def repair_direct_brief(run: dict) -> tuple[dict, bool]:
    """Normalize direct briefs created before grounding enforcement was added."""
    brief = deepcopy(run['brief'])
    valid = {entry['key']: entry for entry in run.get('provenance', [])}
    assumptions = list(brief.get('assumptions') or [])
    changed = False
    for section, prefixes in GROUNDED_SECTIONS.items():
        grounded = []
        for item in brief.get(section, []):
            sources = [key for key in item.get('sources', []) if key in valid and key[0] in prefixes]
            if sources:
                if sources != item.get('sources', []):
                    changed = True
                grounded.append({**item, 'sources': sources, 'uncited': False})
            else:
                assumptions.append(item['text'])
                changed = True
        brief[section] = grounded
    if brief.get('citation_warnings'):
        brief['citation_warnings'] = []
        changed = True
    brief['assumptions'] = list(dict.fromkeys(assumptions))
    return brief, changed

@router.post('')
def build(request: Request, body: RequestIn):
    s = current(request)
    if not llm.config.OPENAI_API_KEY:
        raise RuntimeError('Set OPENAI_API_KEY in .env and restart the server.')
    out = pipeline.start_draft(s, body.project_id, body.request, body.request + ' ' + body.clarification)
    run = out['run']
    selected = include_selected_lessons(s, body.project_id, run['provenance'], body.lesson_ids)
    entries = selected + [{'key':'U1','type':'user','id':run['_id'],'revision':1,'text':body.request + '\n' + body.clarification}]
    runs.update(s, run['_id'], {'provenance': entries, 'author': {'kind':'openai'}})
    value, usage = llm.draft(body.request, brief_mod.context_block(selected) + '\n[U1] User request: ' + body.request + '\n' + body.clarification, body.clarification)
    payload = ground_direct_payload(value, {entry['key'] for entry in entries})
    pipeline.save_brief(s, run['_id'], payload)
    return runs.update(s, run['_id'], {'usage':usage, 'model':llm.config.OPENAI_BRIEF_MODEL, 'clarification_text':body.clarification})

def allowed_inline_script(script):
    return (not (set(script.attrs) - {'type'})
            and script.get('type', '').lower() in ('', 'text/javascript', 'application/javascript'))

def safe_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(['iframe','object','embed','base','link','meta']): tag.decompose()
    for script in soup.find_all('script'):
        if not allowed_inline_script(script):
            script.decompose()
        else:
            script.attrs = {}
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith('on') or attr.lower() in ('src','srcset','href','action','formaction','srcdoc'):
                del tag.attrs[attr]
    # Inline behavior runs in an opaque-origin iframe. Resource, connection and form access stay blocked.
    policy = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; font-src 'none'; form-action 'none'; base-uri 'none'"
    return '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'+policy+'"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>'+str(soup)+'</body></html>'

def validate_interactive_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    if soup.select('button, input, select, textarea') and not any(
        script.get_text(strip=True) for script in soup.find_all('script') if allowed_inline_script(script)
    ):
        raise ValueError('Generated controls have no client-side behavior. Rebuild the artifact.')

@router.post('/{run_id}/preview')
def preview(request: Request, run_id: str):
    s = current(request)
    run = runs.get(s, run_id)
    if run.get('author', {}).get('kind') == 'openai' and run.get('brief'):
        repaired, changed = repair_direct_brief(run)
        if changed:
            run = runs.update(s, run_id, {'brief': repaired, 'status': 'draft', 'artifact': None,
                                           'brief_revision': run.get('brief_revision', 0) + 1})
    if (run.get('artifact') and run['artifact'].get('brief_revision') == run.get('brief_revision')
            and run['artifact'].get('version') == ARTIFACT_VERSION):
        pipeline.export(s, run_id)
        return run
    md = pipeline.export(s, run_id)
    locked = get_db().runs.update_one({'_id':run_id, 'generating':{'$ne':True}}, {'$set':{'generating':True}})
    if not locked.modified_count: raise Conflict('Generation already in progress.')
    try:
        result, usage = llm.website(md)
        validate_interactive_html(result.html)
        latest = runs.get(s, run_id)
        if latest.get('brief_revision') != run.get('brief_revision'):
            raise Conflict('Brief changed during generation; generate again.')
        pipeline.export(s, run_id)  # memory may have changed during the provider call
        return runs.update(s, run_id, {'artifact':{'html':safe_html(result.html),'version':ARTIFACT_VERSION,'brief_revision':run.get('brief_revision'),'created_at':now(),'usage':usage,'model':llm.config.OPENAI_GENERATION_MODEL}})
    finally:
        get_db().runs.update_one({'_id':run_id},{'$set':{'generating':False}})
