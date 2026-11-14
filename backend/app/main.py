from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import config, errors
from app.repo.bootstrap import ensure_demo_workspace
from app.routes import demo, build, agent_tools, auth, lessons, projects, runs, voice


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_demo_workspace()
    yield


app = FastAPI(title="PromptForge", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, same_site="lax")
errors.install(app)

for module in (demo, build, auth, projects, runs, lessons, voice, agent_tools):
    app.include_router(module.router, prefix="/api")

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
