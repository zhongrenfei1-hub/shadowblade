"""Notification-tests shared fixtures.

Strategy
--------

The repo ships a single dev SQLite at ``backend/shadowblade.db`` that
every test in this tree shares. Rather than spin up a per-test DB (which
would require monkey-patching the engine before any module imports
:func:`app.core.db.SessionLocal`), we isolate notification tests by
**workspace id**: each test gets a unique integer from
:data:`UNIQUE_WS_OFFSET` upwards, and every helper / TestClient call
sends it via the ``X-Workspace-Id`` header. The notifications service
filters by workspace on every read, so this gives perfect isolation
without DB juggling.

A ``cleanup`` autouse fixture deletes any rows the test wrote at the
end, so the shared DB doesn't accumulate notification garbage across
test runs.
"""

from __future__ import annotations

import asyncio
import itertools
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make sure backend/ is on sys.path even when pytest is launched from the
# repo root (matches what tests/template/conftest.py does).
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.notification import Notification  # noqa: E402

UNIQUE_WS_OFFSET = 50_000
UNIQUE_USER_OFFSET = 50_000

_ws_counter = itertools.count(UNIQUE_WS_OFFSET)
_user_counter = itertools.count(UNIQUE_USER_OFFSET)


@pytest.fixture
def test_workspace_id() -> int:
    """Unique workspace id for the current test.

    Re-used by every helper that talks to the API so a test's writes are
    completely invisible to its neighbours.
    """
    return next(_ws_counter)


@pytest.fixture
def test_user_id() -> int:
    """Unique user id for the current test."""
    return next(_user_counter)


@pytest.fixture
def client() -> TestClient:
    """Plain TestClient — no headers attached; tests pass them per-call."""
    return TestClient(app)


@pytest.fixture
def auth_headers(test_workspace_id: int, test_user_id: int) -> dict[str, str]:
    """Header bag matching the deps.py convention."""
    return {
        "X-Workspace-Id": str(test_workspace_id),
        "X-User-Id": str(test_user_id),
    }


@pytest.fixture(autouse=True)
def cleanup_notifications(test_workspace_id: int):
    """Delete every notification row this test created on exit.

    Runs *after* the test body so assertions still see the rows they
    inserted. The DELETE is workspace-scoped so it can never wipe other
    tests' fixtures.
    """
    yield
    asyncio.get_event_loop_policy()  # ensure a policy is set
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_purge(test_workspace_id))
    finally:
        loop.close()


async def _purge(workspace_id: int) -> None:
    from sqlalchemy import delete

    async with SessionLocal() as session:
        await session.execute(
            delete(Notification).where(Notification.workspace_id == workspace_id)
        )
        await session.commit()
