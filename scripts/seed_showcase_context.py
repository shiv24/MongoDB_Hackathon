"""Install two simple specs. Keeps decisions, lessons, users and history intact."""
from pathlib import Path
import httpx
root = Path(__file__).resolve().parents[1]
with httpx.Client(base_url='http://localhost:8018/api', timeout=150) as client:
    client.post('/login', json={'user_id':'alice'}).raise_for_status()
    response = client.get('/projects/lumen-signup/context')
    response.raise_for_status()
    sources = response.json()['sources']
    for title, filename in [('Customer exports — product requirements','CUSTOMER_EXPORTS.md'),
                            ('Invoice exports — product requirements','INVOICE_EXPORTS.md')]:
        text = (root/'docs'/filename).read_text()
        existing = next((s for s in sources if s['title'] == title), None)
        if existing:
            response = client.get('/projects/lumen-signup/sources/'+existing['source_id'])
            response.raise_for_status()
            if response.json()['text'].strip() == text.strip():
                print(title+': already current')
                continue
        response = client.post('/projects/lumen-signup/sources',json={'title':title,'text':text,'kind':'spec'})
        response.raise_for_status()
        print(title+': revision '+str(response.json()['revision']))
print('Ready. Allow Atlas indexing time before the next request.')
