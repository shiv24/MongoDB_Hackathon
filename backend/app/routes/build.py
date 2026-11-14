"""Direct typed workflow; generated previews are inert documents."""
from copy import deepcopy

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from app.agent import pipeline, llm, brief as brief_mod
from app.repo import runs
from app.db import get_db, now
from app.session import current
from app.errors import Conflict
router = APIRouter(prefix='/build')

GROUNDED_SECTIONS = {
    'requirements': {'S', 'D', 'U'},
    'current_decisions': {'D'},
    'implementation_context': {'S', 'D'},
    'preferences': {'L'},
}

class RequestIn(BaseModel):
    project_id: str
    request: str = Field(min_length=1, max_length=8000)
    clarification: str = Field(default='', max_length=8000)


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
    entries = run['provenance'] + [{'key':'U1','type':'user','id':run['_id'],'revision':1,'text':body.request + '\n' + body.clarification}]
    runs.update(s, run['_id'], {'provenance': entries, 'author': {'kind':'openai'}})
    value, usage = llm.draft(body.request, out['context'] + '\n[U1] User request: ' + body.request + '\n' + body.clarification, body.clarification)
    payload = ground_direct_payload(value, {entry['key'] for entry in entries})
    pipeline.save_brief(s, run['_id'], payload)
    return runs.update(s, run['_id'], {'usage':usage, 'model':llm.config.OPENAI_BRIEF_MODEL, 'clarification_text':body.clarification})

def safe_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all(['script','iframe','object','embed','base','link','meta']): tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith('on') or attr.lower() in ('src','srcset','href','action','formaction','srcdoc'):
                del tag.attrs[attr]
    # CSP comes first, before any generated content; iframe also has an empty sandbox.
    policy = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; form-action 'none'; base-uri 'none'"
    return '<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="'+policy+'"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>'+str(soup)+'</body></html>'

@router.post('/{run_id}/preview')
def preview(request: Request, run_id: str):
    s = current(request)
    run = runs.get(s, run_id)
    if run.get('author', {}).get('kind') == 'openai' and run.get('brief'):
        repaired, changed = repair_direct_brief(run)
        if changed:
            run = runs.update(s, run_id, {'brief': repaired, 'status': 'draft', 'artifact': None,
                                           'brief_revision': run.get('brief_revision', 0) + 1})
    if run.get('artifact') and run['artifact'].get('brief_revision') == run.get('brief_revision'):
        pipeline.export(s, run_id)
        return run
    md = pipeline.export(s, run_id)
    locked = get_db().runs.update_one({'_id':run_id, 'generating':{'$ne':True}}, {'$set':{'generating':True}})
    if not locked.modified_count: raise Conflict('Generation already in progress.')
    try:
        result, usage = llm.website(md)
        latest = runs.get(s, run_id)
        if latest.get('brief_revision') != run.get('brief_revision'):
            raise Conflict('Brief changed during generation; generate again.')
        pipeline.export(s, run_id)  # memory may have changed during the provider call
        return runs.update(s, run_id, {'artifact':{'html':safe_html(result.html),'brief_revision':run.get('brief_revision'),'created_at':now(),'usage':usage,'model':llm.config.OPENAI_GENERATION_MODEL}})
    finally:
        get_db().runs.update_one({'_id':run_id},{'$set':{'generating':False}})
