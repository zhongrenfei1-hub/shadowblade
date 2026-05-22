from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api import (
    analytics,
    assets,
    auth,
    brand_kits,
    generate,
    google_auth,
    health,
    integrations,
    jobs,
    keys,
    mix_video,
    notifications,
    organizations,
    projects,
    render_queue,
    settings as settings_api,
    stock,
    templates,
    workbench,
    workspaces,
)
from app.core import secrets
from app.core.config import settings
from app.core.db import engine, init_db

# Mirror persisted secrets into os.environ before anything reads them.
secrets.load_into_env()


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

# SessionMiddleware backs Authlib's OAuth flow — it stashes ``state`` and
# the PKCE ``code_verifier`` in a signed cookie between the
# ``/auth/google/login`` redirect and the ``/auth/google/callback``
# return trip. ``session_secret_key`` defaults to ``jwt_secret`` (see
# config.get_settings); production deployments can split them by setting
# SHADOWBLADE_SESSION_SECRET_KEY.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    https_only=settings.environment == "production",
    same_site="lax",  # the cross-site Google → us redirect needs lax, not strict
    max_age=10 * 60,  # the dance completes in seconds; 10 min covers slow consent
)

for router in (
    health.router,
    auth.router,
    google_auth.router,
    workspaces.router,
    organizations.router,
    projects.router,
    jobs.router,
    assets.router,
    templates.router,
    render_queue.router,
    brand_kits.router,
    analytics.router,
    mix_video.router,
    generate.router,
    stock.router,
    keys.router,
    notifications.router,
    integrations.router,
    settings_api.router,
    workbench.router,
):
    app.include_router(router, prefix="/api/v1")

# Serve the rendered MP4 + cover output directory so the frontend's <video>
# can stream the result by HTTP. Path is relative to the backend's CWD —
# matches Settings.storage_root default of "./storage".
_storage_root = Path(settings.storage_root).resolve()
_storage_root.mkdir(parents=True, exist_ok=True)
app.mount("/static/storage", StaticFiles(directory=str(_storage_root)), name="storage")
