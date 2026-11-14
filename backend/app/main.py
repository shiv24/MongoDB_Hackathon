from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.routes import auth, lessons, projects, runs, voice

app = FastAPI(title="PromptForge")
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)

for module in (auth, projects, runs, lessons, voice):
    app.include_router(module.router)
