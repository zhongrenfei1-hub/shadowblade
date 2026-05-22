"""Shared fixtures for Workbench tests.

Mirrors the per-test isolated SQLite + dependency override pattern used by
the brand-kit, settings and organizations test suites. Each test gets a
fresh DB file under ``tmp_path`` so reads never see fixtures from another
test, and the FastAPI ``get_db`` dependency is overridden to bind to that
engine for the duration of the test client.

A small `seed_projects` fixture is provided so individual tests don't have
to re-create the same handful of Project rows when exercising
``/workbench/recent-projects`` and ``/workbench/active-tasks``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import deps as deps_module
from app.core import config as config_module
from app.core.db import Base, _apply_dev_migrations_sync


@pytest_asyncio.fixture
async def isolated_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Throw-away async engine on tmp SQLite; storage_root rerouted to tmp."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(
        config_module.settings, "storage_root", str(storage_root), raising=True
    )

    # Touch every model so its table joins Base.metadata before create_all.
    from app import models  # noqa: F401
    from app.models import (  # noqa: F401
        asset,
        brand_kit,
        invitation,
        job,
        membership,
        project,
        render,
        template,
        user,
        workspace,
    )

    engine = create_async_engine(db_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(_apply_dev_migrations_sync)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def isolated_db(isolated_engine):
    """TestClient bound to the throw-away engine via dependency override."""
    from app.main import app

    session_factory = async_sessionmaker(isolated_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[deps_module.get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(deps_module.get_db, None)


@pytest.fixture
def workspace_headers() -> dict[str, str]:
    """Headers selecting the demo workspace (id=1)."""
    return {"X-Workspace-Id": "1"}


@pytest.fixture
def user_headers(workspace_headers: dict[str, str]) -> dict[str, str]:
    return {**workspace_headers, "X-User-Id": "42"}


@pytest.fixture
def mix_video_tasks_reset():
    """Clear the in-memory mix-video task registry around a test.

    The Workbench reads from ``app.api.mix_video._TASKS`` so a leaked task
    from a previous test (or a previously interactive dev session) can
    poison assertions. Clear before and after for full isolation.
    """
    from app.api.mix_video import _TASKS

    snapshot = dict(_TASKS)
    _TASKS.clear()
    try:
        yield _TASKS
    finally:
        _TASKS.clear()
        _TASKS.update(snapshot)


@pytest_asyncio.fixture
async def seed_projects(isolated_engine):
    """Insert a stable set of Project + RenderTask rows for two workspaces.

    Returns a dict with the inserted ids so tests can assert against them
    without hard-coding magic numbers. Two workspaces are seeded so
    cross-workspace isolation tests have something to discriminate.
    """
    from app.models.project import Project
    from app.models.render import RenderTask

    now = datetime.now(timezone.utc)
    session_factory = async_sessionmaker(isolated_engine, expire_on_commit=False)

    async with session_factory() as s:
        # Workspace 1 — three projects of decreasing freshness
        p1 = Project(
            workspace_id=1, owner_id=1, name="春季产品发布",
            purpose="marketing", brief="智能腕环 9:16 主推视频",
            aspect_ratio="9:16", duration_seconds=30, voice="alloy-en-female",
            status="rendering", updated_at=now,
        )
        p2 = Project(
            workspace_id=1, owner_id=1, name="AI Copilot 60 秒演示",
            purpose="product_demo", brief="销售场景产品演示",
            aspect_ratio="16:9", duration_seconds=60, voice="ember-en-male",
            status="scripting", updated_at=now - timedelta(hours=2),
        )
        p3 = Project(
            workspace_id=1, owner_id=1, name="入职培训训练营",
            purpose="training", brief="销售工程师入职",
            aspect_ratio="16:9", duration_seconds=180, voice="alloy-en-female",
            status="done", updated_at=now - timedelta(days=1),
        )
        # Workspace 2 — different tenant, should never leak into workspace 1.
        p4 = Project(
            workspace_id=2, owner_id=2, name="另一工作区项目",
            purpose="social", brief="不应出现在 workspace=1 的列表",
            aspect_ratio="9:16", duration_seconds=15, voice="lumen-en-neutral",
            status="draft", updated_at=now,
        )
        s.add_all([p1, p2, p3, p4])
        await s.flush()

        # One running render and one queued for workspace 1's first project.
        r1 = RenderTask(
            project_id=p1.id, priority="rush", status="running",
            progress=0.62, estimated_seconds=64.0, worker="gpu-cluster-3",
            started_at=now - timedelta(minutes=2),
        )
        r2 = RenderTask(
            project_id=p2.id, priority="normal", status="queued",
            progress=0.0, estimated_seconds=180.0,
        )
        # One succeeded render today — feeds the 'renders_today' KPI.
        r3 = RenderTask(
            project_id=p1.id, priority="normal", status="succeeded",
            progress=1.0, estimated_seconds=120.0,
            started_at=now - timedelta(hours=1),
            finished_at=now - timedelta(minutes=30),
            output_url="/static/storage/mix/done.mp4",
        )
        # Workspace 2's render — must not appear in workspace 1 queries.
        r4 = RenderTask(
            project_id=p4.id, priority="high", status="running",
            progress=0.3,
        )
        s.add_all([r1, r2, r3, r4])
        await s.commit()

        return {
            "project_ids": [p1.id, p2.id, p3.id],
            "ws2_project_id": p4.id,
            "render_ids": [r1.id, r2.id, r3.id],
            "ws2_render_id": r4.id,
            "now": now,
        }
