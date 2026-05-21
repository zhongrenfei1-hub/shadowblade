from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    analytics,
    assets,
    auth,
    brand_kits,
    generate,
    health,
    jobs,
    mix_video,
    projects,
    render_queue,
    templates,
    workspaces,
)
from app.core.config import settings
from app.core.db import engine, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield
    await engine.dispose()


app = FastAPI(
    title="ShadowBlade API",
    version="0.1.0",
    description="Enterprise AI short-video generation pipeline.",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    health.router,
    auth.router,
    workspaces.router,
    projects.router,
    jobs.router,
    assets.router,
    templates.router,
    render_queue.router,
    brand_kits.router,
    analytics.router,
    mix_video.router,
    generate.router,
):
    app.include_router(router, prefix="/api/v1")

# Serve the rendered MP4 + cover output directory so the frontend's <video>
# can stream the result by HTTP. Path is relative to the backend's CWD —
# matches Settings.storage_root default of "./storage".
_storage_root = Path(settings.storage_root).resolve()
_storage_root.mkdir(parents=True, exist_ok=True)
app.mount("/static/storage", StaticFiles(directory=str(_storage_root)), name="storage")
