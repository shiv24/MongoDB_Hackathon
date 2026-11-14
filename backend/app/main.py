from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.routes import auth, lessons, runs

app = FastAPI(title="PromptForge")
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)

app.include_router(auth.router)
app.include_router(runs.router)
app.include_router(lessons.router)

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
