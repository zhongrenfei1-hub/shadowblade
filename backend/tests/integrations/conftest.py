"""Shared fixtures for Integrations tests.

Same isolation strategy as ``tests/brand_kit/conftest.py``: build a fresh
async engine bound to a per-test tmp SQLite file, then override the
FastAPI ``get_db`` dependency so every Depends-injected session lands on
that engine. This is much more robust than ``importlib.reload`` because
the module cache stays consistent across tests.

We also override the module-level ``SessionLocal`` that the event
dispatcher uses for its background path, so emit_event sessions hit the
same tmp DB.

Extras provided by this conftest:

* :func:`mock_http_server` — a recording HTTP server on a free port. Tests
  use its URL as the webhook target and assert on the captured requests.
* :func:`api_key_factory`  — mint and return ``(plaintext, body)`` so
  tests can authenticate as the freshly-minted key.
"""

from __future__ import annotations

import http.server
import json
import socket
from pathlib import Path
from threading import Thread
from typing import Any

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

    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(
        config_module.settings, "storage_root", str(storage_root), raising=True
    )

    # Register every model on Base.metadata so create_all sees the full
    # schema. Order doesn't matter — SQLAlchemy resolves FKs lazily.
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
        settings as settings_model,
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
def isolated_db(isolated_engine, monkeypatch: pytest.MonkeyPatch):
    """Return a TestClient whose ``get_db`` depends on the tmp engine.

    Also overrides the module-level ``SessionLocal`` so the event
    dispatcher background path lands on the same DB.
    """
    from app.main import app

    session_factory = async_sessionmaker(isolated_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    # Patch SessionLocal in every place that captured the global one.
    import app.core.db as core_db
    import app.services.integrations.events as events_mod

    monkeypatch.setattr(core_db, "SessionLocal", session_factory, raising=True)
    monkeypatch.setattr(events_mod, "SessionLocal", session_factory, raising=True)

    app.dependency_overrides[deps_module.get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(deps_module.get_db, None)


@pytest.fixture
def workspace_headers() -> dict[str, str]:
    return {"X-Workspace-Id": "1"}


@pytest.fixture
def user_headers(workspace_headers: dict[str, str]) -> dict[str, str]:
    return {**workspace_headers, "X-User-Id": "42"}


# ---------------------------------------------------------------------------
# Mock HTTP server
# ---------------------------------------------------------------------------


class _RecordingHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return  # silence default stderr noise

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else ""
        self.server.received.append(  # type: ignore[attr-defined]
            {
                "path": self.path,
                "headers": {k: v for k, v in self.headers.items()},
                "body": body,
                "json": json.loads(body) if body and body.startswith("{") else None,
            }
        )
        status = getattr(self.server, "response_status", 200)
        payload = getattr(self.server, "response_body", b'{"ok":true}')
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture
def mock_http_server():
    """Start a recording HTTP server on a free port for the test's duration."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    server = http.server.HTTPServer(("127.0.0.1", port), _RecordingHandler)
    server.received = []  # type: ignore[attr-defined]
    server.response_status = 200  # type: ignore[attr-defined]
    server.response_body = b'{"ok":true}'  # type: ignore[attr-defined]

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def set_status(code: int) -> None:
        server.response_status = code  # type: ignore[attr-defined]

    def set_body(raw: bytes | str) -> None:
        server.response_body = raw if isinstance(raw, bytes) else raw.encode("utf-8")  # type: ignore[attr-defined]

    yield {
        "url": f"http://127.0.0.1:{port}/hook",
        "received": server.received,  # type: ignore[attr-defined]
        "set_status": set_status,
        "set_body": set_body,
    }

    server.shutdown()
    server.server_close()


# ---------------------------------------------------------------------------
# API-key factory
# ---------------------------------------------------------------------------


@pytest.fixture
def api_key_factory(isolated_db: TestClient, workspace_headers: dict[str, str]):
    """Create an API key against the test client and return (plaintext, body)."""

    def _make(*, name: str = "Test Key", scopes: list[str] | None = None) -> tuple[str, dict]:
        body: dict[str, Any] = {"name": name}
        if scopes is not None:
            body["scopes"] = scopes
        r = isolated_db.post(
            "/api/v1/integrations/api-keys",
            json=body,
            headers=workspace_headers,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        return data["key"], data

    return _make
