"""Check configuration without printing credentials. --live also probes configured services."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app import config

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    required=['MONGODB_URI','VOYAGE_API_KEY','OPENAI_API_KEY']
    missing=[]
    for key in required+['ELEVENLABS_API_KEY','ELEVENLABS_AGENT_ID','PUBLIC_BASE_URL','SESSION_SECRET']:
        value=getattr(config,key,'')
        ok=bool(value) and '<' not in value and value not in ('dev','change-me')
        print(f'{key}: {"configured" if ok else "missing/placeholder"}')
        if key in required and not ok:missing.append(key)
    print('Typed briefs require Atlas + Voyage + OpenAI. Dictation additionally needs ElevenLabs. Live conversation needs agent setup and HTTPS tunnel.')
    if args.live and not missing:
        from app.db import get_db
        from app.agent import embed
        from openai import OpenAI
        import httpx
        probes={
            'Atlas':lambda:get_db().command('ping'),
            'Voyage embedding':lambda:embed.query('PromptForge connectivity check'),
            'OpenAI model access':lambda:OpenAI(api_key=config.OPENAI_API_KEY,timeout=15,max_retries=0).models.retrieve(config.OPENAI_BRIEF_MODEL),
        }
        if config.ELEVENLABS_API_KEY:
            probes['ElevenLabs']=lambda:httpx.get('https://api.elevenlabs.io/v1/user',headers={'xi-api-key':config.ELEVENLABS_API_KEY},timeout=15).raise_for_status()
        for name,probe in probes.items():
            try:
                value=probe()
                if name=='Voyage embedding' and len(value)!=config.EMBED_DIMS:raise ValueError('dimension mismatch')
                print(name+': OK')
            except Exception as e:
                print(name+': FAILED ('+type(e).__name__+'); check credentials, access and network')
                missing.append(name)
        print('Live probes do not validate the full conversation or generation workflow. Voyage probe uses a small number of tokens.')
    return 1 if missing else 0
if __name__=='__main__':sys.exit(main())
