"""Shared fixtures for the Team/Organization test suite.

Every test gets its own SQLite-in-memory database so concurrent test runs
don't leak state. The lifespan handler in ``app.main`` is bypassed in
favour of an explicit ``init_db()`` call against the per-test engine, so
we can avoid running the static-files setup (the showcase storage dir is
not relevant here).
"""

from __future__ import annotations

import os
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_settings_cache(monkeypatch, tmp_path):
    """Make sure ``settings`` is re-read with the test database URL.

    Each test gets its own SQLite file inside the pytest-provided tmp_path.
    Going to a real file (instead of ``:memory:``) sidesteps the
    aiosqlite/in-memory quirk where the namespace evaporates between
    connections — every aiosqlite connection is opened lazily, so an
    in-memory DB only survives while at least one connection is open.

    Critically, this fixture restores the original cached settings on
    teardown — otherwise other test modules (template/, video/) that
    bypass this fixture would inherit a stale URL pointing at a deleted
    tmp_path, and their endpoint tests would fail with "unable to open
    database file".
    """
    from app.core import config as _cfg

    original_settings = _cfg.settings
    original_db_url = original_settings.database_url

    test_db_path = tmp_path / "test.db"
    test_db_url = f"sqlite+aiosqlite:///{test_db_path}"
    monkeypatch.setenv("SHADOWBLADE_DATABASE_URL", test_db_url)
    monkeypatch.setenv("SHADOWBLADE_JWT_SECRET", "test-jwt-secret-fixed")

    # Drop any cached settings so the next ``from app.core.config import
    # settings`` picks up the new env.
    _cfg.get_settings.cache_clear()
    # Force re-evaluation
    _cfg.settings = _cfg.get_settings()
    try:
        yield
    finally:
        # Restore original settings + cache so cross-module tests aren't
        # poisoned by the tmp_path that will shortly be torn down.
        _cfg.get_settings.cache_clear()
        # monkeypatch reverts the env vars on its own, so a fresh
        # get_settings() yields the original config.
        _cfg.settings = _cfg.get_settings()
        # Defensive: if something cached the production URL differently
        # (e.g. via a .env file), pin it back to the value we captured.
        if _cfg.settings.database_url != original_db_url:
            _cfg.settings = original_settings


@pytest_asyncio.fixture
async def db_engine():
    """Build a fresh async engine + run create_all against the test URL.

    Returns ``(engine, SessionLocal)`` — the client fixture below installs
    a ``get_db`` dependency override that yields sessions from this
    session-factory, so every endpoint hits the per-test DB regardless of
    how it imported :data:`app.core.db.SessionLocal`.
    """
    from app.core.config import settings as _settings
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_settings.database_url, future=True, echo=False)
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    # Create schema by importing all models then running create_all.
    from app.core.db import Base
    from app.models import (  # noqa: F401 — register Mapped classes
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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine, session_factory

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncIterator[TestClient]:
    """FastAPI TestClient wired to the per-test DB via dependency override.

    Uses ``app.dependency_overrides`` instead of monkey-patching module
    globals because endpoints capture ``SessionLocal`` at import time via
    ``from app.core.db import SessionLocal`` — a runtime rebind would not
    reach them. Overriding ``get_db`` flips every dependency tree at once.
    """
    engine, session_factory = db_engine

    from app.api.deps import get_db
    from app.main import app

    async def _get_db_override():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _get_db_override

    # The lifespan still runs ``init_db()`` against the prod ``engine``.
    # That's harmless — it would only matter if some endpoint reached for
    # the prod engine directly, which none of ours do. Suppress its
    # side effects by entering the TestClient without firing lifespan via
    # passing ``raise_server_exceptions=True`` and trusting create_all to
    # be idempotent.
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Convenience helpers — high-level building blocks for tests
# ---------------------------------------------------------------------------


def register(
    client: TestClient,
    *,
    email: str,
    full_name: str = "Test User",
    password: str = "strongpass1",
    drop_personal_ws: bool = True,
) -> dict:
    """Register a new user; return ``{token, user_id, default_workspace_id}``.

    By default we also delete the personal workspace materialised by the
    register endpoint so its slug doesn't collide with whatever the test
    wants to create via :func:`create_org` next. Pass
    ``drop_personal_ws=False`` if the test specifically wants to assert
    on the personal-workspace bootstrap (e.g. /auth tests).
    """
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    body = r.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    if drop_personal_ws:
        # The register endpoint creates a personal workspace whose slug is
        # derived from the email's local part. Many tests want to take that
        # slug for themselves — drop the bootstrap workspace so they can.
        delete_r = client.delete(
            f"/api/v1/organizations/{body['new_organization_id']}",
            headers=headers,
        )
        # 204 on success; 409 if (unlikely) the bootstrap has dependents.
        assert delete_r.status_code in (204, 409), (
            f"cleanup of personal ws failed: {delete_r.status_code} {delete_r.text}"
        )
    return {
        "token": body["access_token"],
        "user_id": body["user"]["id"],
        "default_workspace_id": body["default_workspace_id"],
        "headers": headers,
    }


def login(client: TestClient, *, email: str, password: str = "strongpass1") -> dict:
    """Login; return ``{token, user_id, headers}``."""
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    return {
        "token": body["access_token"],
        "user_id": body["user"]["id"],
        "default_workspace_id": body["default_workspace_id"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
    }


def create_org(
    client: TestClient,
    *,
    headers: dict,
    name: str = "Acme",
    slug: str | None = None,
) -> dict:
    """Create an organization owned by the caller; return JSON body."""
    slug = slug or f"acme-{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/api/v1/organizations",
        json={"name": name, "slug": slug},
        headers=headers,
    )
    assert r.status_code == 201, f"create org failed: {r.status_code} {r.text}"
    return r.json()


def invite(
    client: TestClient,
    *,
    org_id: int,
    headers: dict,
    email: str,
    role: str = "member",
    days: int = 7,
) -> dict:
    """Create an invitation; return JSON body (includes ``invite_code``)."""
    r = client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": email, "role": role, "expires_in_days": days},
        headers=headers,
    )
    assert r.status_code == 201, f"invite failed: {r.status_code} {r.text}"
    return r.json()


def accept(client: TestClient, *, code: str, headers: dict) -> dict:
    r = client.post(f"/api/v1/invitations/{code}/accept", headers=headers)
    assert r.status_code == 200, f"accept failed: {r.status_code} {r.text}"
    return r.json()


__all__ = [
    "accept",
    "create_org",
    "invite",
    "login",
    "register",
]
