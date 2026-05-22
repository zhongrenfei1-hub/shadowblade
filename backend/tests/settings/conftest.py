"""Shared fixtures for the Settings test suite.

Mirrors :mod:`tests.brand_kit.conftest` — an isolated SQLite database per
test, a TestClient bound to a session factory pointing at that database,
and convenience header fixtures.

We additionally seed a real ``WorkspaceMember`` row for the user header
fixture so the ``require_workspace_role`` permission gate can validate
the path without needing the ``X-Workspace-Role`` override on every
single call.
"""

from __future__ import annotations

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
    """A throw-away async SQLAlchemy engine on a temp SQLite file."""
    db_path = tmp_path / "settings_test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(
        config_module.settings, "storage_root", str(storage_root), raising=True
    )

    # Eager import so create_all sees every Mapped class. ``settings`` is
    # imported via the package alias to dodge the local ``config.settings``.
    from app import models  # noqa: F401
    from app.models import (  # noqa: F401
        asset,
        brand_kit,
        integration,
        invitation,
        job,
        membership,
        notification,
        project,
        render,
        settings as settings_model,  # noqa: F401
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
def session_factory(isolated_engine):
    return async_sessionmaker(isolated_engine, expire_on_commit=False)


@pytest.fixture
def isolated_db(isolated_engine, session_factory):
    """``TestClient`` whose ``get_db`` yields from the isolated engine."""
    from app.main import app

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


# ---------------------------------------------------------------------------
# Header bundles — sit on top of the demo workspace (id=1) so the existing
# brand-kit / mix-video flows keep working without test setup changes.
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_headers() -> dict[str, str]:
    """Headers selecting the default demo workspace.

    In this workspace, role resolution falls back to 'admin' so PATCH
    endpoints work without seeding a membership row.
    """
    return {"X-Workspace-Id": "1"}


@pytest.fixture
def user_headers(workspace_headers: dict[str, str]) -> dict[str, str]:
    """Workspace + user headers."""
    return {**workspace_headers, "X-User-Id": "42"}


@pytest.fixture
def admin_headers(user_headers: dict[str, str]) -> dict[str, str]:
    """Headers carrying an explicit admin role override.

    Distinct from the default user_headers because some tests want to
    assert role gates *without* relying on the demo-workspace fallback.
    """
    return {**user_headers, "X-Workspace-Role": "admin"}


@pytest.fixture
def member_headers(user_headers: dict[str, str]) -> dict[str, str]:
    """Member-role headers — useful for verifying 403 on admin endpoints."""
    return {**user_headers, "X-Workspace-Role": "member"}


@pytest.fixture
def guest_headers(workspace_headers: dict[str, str]) -> dict[str, str]:
    return {**workspace_headers, "X-User-Id": "99", "X-Workspace-Role": "guest"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seeded_workspace(session_factory):
    """Insert workspaces (id=1 demo + id=2 secondary) for cross-workspace
    isolation tests. SQLite without explicit ``PRAGMA foreign_keys=ON``
    tolerates missing FK targets, so most tests don't need this — opt in
    only when an integrity assertion depends on the row existing.
    """
    from app.models.workspace import Workspace

    async with session_factory() as db:
        db.add_all(
            [
                Workspace(id=1, slug="demo", name="Demo Workspace"),
                Workspace(id=2, slug="other", name="Other Workspace"),
            ]
        )
        await db.commit()
    return [1, 2]
