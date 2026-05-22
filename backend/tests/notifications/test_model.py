"""Model-layer tests for Notification.

Confirms the SQLAlchemy mapping matches the schema declared in
:mod:`app.models.notification` — column constraints, JSON round-trip,
default values, and index-backed query plans. These run in-process so
they're cheap and form the regression net for ORM-level mistakes.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.notification import (
    NOTIFICATION_CATEGORIES,
    NOTIFICATION_KINDS,
    NOTIFICATION_TYPES,
    Notification,
)


pytestmark = pytest.mark.asyncio


async def _persist(**kwargs) -> Notification:
    row = Notification(**kwargs)
    async with SessionLocal() as session:
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def test_create_basic_row(test_workspace_id: int, test_user_id: int):
    row = await _persist(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="video_generated",
        category="pipeline",
        kind="done",
        title="渲染完成",
        message="耗时 5.5s",
    )
    assert row.id is not None
    assert row.read is False
    assert row.archived is False
    assert row.created_at is not None


async def test_payload_round_trip(test_workspace_id: int, test_user_id: int):
    payload = {
        "task_id": "abc123",
        "project_id": 99,
        "duration": 12.5,
        "nested": {"a": 1, "b": [1, 2, 3]},
    }
    row = await _persist(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="video_generated",
        category="pipeline",
        kind="done",
        title="渲染完成",
        payload=payload,
    )
    async with SessionLocal() as session:
        fetched = (
            await session.execute(
                select(Notification).where(Notification.id == row.id)
            )
        ).scalars().first()
    assert fetched is not None
    assert fetched.payload == payload


async def test_enum_constants_are_distinct_strings():
    # If any enum gets a typo'd duplicate we want the test suite to scream
    # before frontend filters silently break. (We don't require the three
    # sets to be disjoint — "billing" is intentionally both a type and a
    # category/kind because the React mock collapses those two axes for
    # billing-flavoured events.)
    assert len(NOTIFICATION_TYPES) == len(set(NOTIFICATION_TYPES))
    assert len(NOTIFICATION_CATEGORIES) == len(set(NOTIFICATION_CATEGORIES))
    assert len(NOTIFICATION_KINDS) == len(set(NOTIFICATION_KINDS))


async def test_default_message_is_empty_string(
    test_workspace_id: int, test_user_id: int
):
    row = await _persist(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        category="system",
        kind="info",
        title="A",
    )
    assert row.message == ""


async def test_default_payload_is_empty_dict(
    test_workspace_id: int, test_user_id: int
):
    row = await _persist(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        category="system",
        kind="info",
        title="A",
    )
    assert row.payload == {}


async def test_workspace_broadcast_user_id_nullable(test_workspace_id: int):
    """A user_id=NULL row is a workspace-wide broadcast (no recipient yet)."""
    row = await _persist(
        workspace_id=test_workspace_id,
        user_id=None,
        type="billing",
        category="billing",
        kind="billing",
        title="季度结算",
    )
    assert row.user_id is None


async def test_query_filter_by_workspace_is_isolated(
    test_workspace_id: int, test_user_id: int
):
    other_ws = test_workspace_id + 999_999
    await _persist(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        category="system",
        kind="info",
        title="mine",
    )
    await _persist(
        workspace_id=other_ws,
        user_id=test_user_id,
        type="system",
        category="system",
        kind="info",
        title="not mine",
    )
    async with SessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(Notification).where(
                        Notification.workspace_id == test_workspace_id
                    )
                )
            )
            .scalars()
            .all()
        )
        # Clean up the foreign workspace row we created so we don't pollute
        # the shared DB.
        from sqlalchemy import delete

        await session.execute(
            delete(Notification).where(Notification.workspace_id == other_ws)
        )
        await session.commit()
    assert len(rows) == 1
    assert rows[0].title == "mine"
