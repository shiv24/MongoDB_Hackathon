from fastapi import APIRouter, Request
from app.repo import demo
from app.session import current

router = APIRouter(prefix='/demo')

@router.post('/start')
def start(request: Request):
    current(request)
    user, run = demo.start()
    request.session.clear()
    request.session.update(user_id=user['_id'])
    return {'user_id':user['_id'], 'project_id':run['project_id'], 'run_id':run['_id']}
