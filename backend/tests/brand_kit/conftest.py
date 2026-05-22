"""Shared fixtures for Brand Kit tests.

These tests need an isolated SQLite database so they don't poison cross-
test state. Strategy:

1. Create a fresh ``sqlite+aiosqlite:///<tmp>/db.sqlite`` engine per test.
2. Run ``Base.metadata.create_all`` against it.
3. Build a session factory bound to *this* engine.
4. Override the FastAPI ``get_db`` dependency to yield from that factory.
5. Override ``settings.storage_root`` so logo uploads land under tmp_path
   (otherwise the test would write into the real ``storage/`` folder).

This avoids ``importlib.reload`` (which is order-sensitive and brittle in
async land) and keeps the production app's startup path identical to
what we test.
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
    """Build a throw-away async SQLAlchemy engine on a tmp SQLite file."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    # Re-route uploads to tmp_path so the real ``storage/`` stays clean.
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(
        config_module.settings, "storage_root", str(storage_root), raising=True
    )

    # Ensure all models are imported (registers them on Base.metadata) before
    # create_all runs — otherwise the brand_kits table is missing.
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
    """Return a :class:`TestClient` whose ``get_db`` depends on the tmp engine."""
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
    """Headers selecting the default demo workspace.

    Centralised so tests stay readable when we later swap the demo-workspace
    sentinel for real JWT-derived workspace ids.
    """
    return {"X-Workspace-Id": "1"}


@pytest.fixture
def user_headers(workspace_headers: dict[str, str]) -> dict[str, str]:
    """Workspace + user headers — for tests that exercise user-scoped kits."""
    return {**workspace_headers, "X-User-Id": "42"}


@pytest.fixture
def png_bytes() -> bytes:
    """A tiny valid 1×1 PNG used by logo-upload tests.

    Rendered through Pillow at import time so the bytes are byte-perfect
    against the same library the API uses for decode validation.
    """
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (1, 1), (15, 42, 74, 255)).save(buf, format="PNG")
    return buf.getvalue()
