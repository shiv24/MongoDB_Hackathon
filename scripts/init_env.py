"""Create ignored local configuration without overwriting existing keys."""
from pathlib import Path
import os
import secrets
root=Path(__file__).resolve().parents[1]
target=root/'.env'
if target.exists():
    print('Existing .env preserved. Add missing settings from .env.example manually.')
else:
    text=(root/'.env.example').read_text()
    lines=[]
    for line in text.splitlines():
        if line.startswith(('SESSION_SECRET=', 'AGENT_TOOL_SECRET=')):
            line=line.split('=',1)[0]+'='+secrets.token_urlsafe(48)
        lines.append(line)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write('\n'.join(lines)+'\n')
    print('Created ignored .env with generated session secrets. Fill provider keys locally.')
