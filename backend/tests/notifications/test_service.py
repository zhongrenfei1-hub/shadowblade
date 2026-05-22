"""Service-layer tests — CRUD primitives + event helpers.

Covers what the REST router and the trigger hooks rely on:
    * create / list / mark-read / mark-all-read / delete / archive
    * fan-out fan-in for broadcast events
    * category & type filtering
    * pagination semantics
    * the ``_swallow`` decorator that keeps trigger helpers from crashing
      a failing parent request
"""

from __future__ import annotations

import pytest

from app.services import notifications as svc

pytestmark = pytest.mark.asyncio


async def test_create_basic(test_workspace_id: int, test_user_id: int):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="video_generated",
        title="✓",
    )
    assert row.id is not None
    assert row.category == "pipeline"  # derived from type
    assert row.kind == "done"           # default kind for video_generated


async def test_create_override_category_and_kind(
    test_workspace_id: int, test_user_id: int
):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="维护通知",
        category="billing",  # override
        kind="warn",          # override
    )
    assert row.category == "billing"
    assert row.kind == "warn"


async def test_create_rejects_unknown_type(test_workspace_id: int, test_user_id: int):
    with pytest.raises(ValueError):
        await svc.create_notification(
            workspace_id=test_workspace_id,
            user_id=test_user_id,
            type="not_a_real_type",  # type: ignore[arg-type]
            title="X",
        )


async def test_list_returns_newest_first(
    test_workspace_id: int, test_user_id: int
):
    titles = []
    for i in range(5):
        row = await svc.create_notification(
            workspace_id=test_workspace_id,
            user_id=test_user_id,
            type="system",
            title=f"t{i}",
        )
        titles.append(row.title)
    items, total, _unread = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id, limit=10
    )
    assert total == 5
    # Newest first → reverse of insertion order
    assert [it.title for it in items[:5]] == list(reversed(titles))


async def test_list_pagination_offset(test_workspace_id: int, test_user_id: int):
    for i in range(7):
        await svc.create_notification(
            workspace_id=test_workspace_id,
            user_id=test_user_id,
            type="system",
            title=f"t{i}",
        )
    page1, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id, limit=3, offset=0
    )
    page2, _, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id, limit=3, offset=3
    )
    assert total == 7
    assert len(page1) == 3
    assert len(page2) == 3
    # No overlap between pages
    ids1 = {n.id for n in page1}
    ids2 = {n.id for n in page2}
    assert ids1.isdisjoint(ids2)


async def test_list_filter_unread_only(test_workspace_id: int, test_user_id: int):
    r1 = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="read",
    )
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="unread",
    )
    # Mark only the first as read
    await svc.mark_read(
        notification_id=r1.id,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    items, _, _ = await svc.list_notifications(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        unread_only=True,
    )
    titles = [n.title for n in items]
    assert "unread" in titles
    assert "read" not in titles


async def test_list_filter_by_category(test_workspace_id: int, test_user_id: int):
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="video_generated",
        title="pipeline event",
    )
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="billing",
        title="billing event",
    )
    items, _, _ = await svc.list_notifications(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        category="pipeline",
    )
    titles = [n.title for n in items]
    assert titles == ["pipeline event"]


async def test_list_filter_by_type(test_workspace_id: int, test_user_id: int):
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="video_generated",
        title="vg",
    )
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="brand_kit_changed",
        title="bk",
    )
    items, _, _ = await svc.list_notifications(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="brand_kit_changed",
    )
    assert [n.title for n in items] == ["bk"]


async def test_list_excludes_archived_by_default(
    test_workspace_id: int, test_user_id: int
):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="archive me",
    )
    await svc.archive_notification(
        notification_id=row.id,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    items, _, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id
    )
    assert all(n.id != row.id for n in items)
    # Opting in returns it again
    items2, _, _ = await svc.list_notifications(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        include_archived=True,
    )
    assert any(n.id == row.id for n in items2)


async def test_mark_read_sets_read_at(test_workspace_id: int, test_user_id: int):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="mark me",
    )
    assert row.read is False and row.read_at is None
    updated = await svc.mark_read(
        notification_id=row.id,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    assert updated is not None
    assert updated.read is True
    assert updated.read_at is not None


async def test_mark_read_idempotent(test_workspace_id: int, test_user_id: int):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="x",
    )
    first = await svc.mark_read(
        notification_id=row.id,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    second = await svc.mark_read(
        notification_id=row.id,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    assert first.read_at == second.read_at  # second call didn't reset the timestamp


async def test_mark_read_returns_none_for_foreign_workspace(
    test_workspace_id: int, test_user_id: int
):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="x",
    )
    # Same id, different workspace — must not be flippable.
    other_ws = test_workspace_id + 999
    result = await svc.mark_read(
        notification_id=row.id,
        workspace_id=other_ws,
        user_id=test_user_id,
    )
    assert result is None


async def test_mark_all_read_returns_count(
    test_workspace_id: int, test_user_id: int
):
    for i in range(4):
        await svc.create_notification(
            workspace_id=test_workspace_id,
            user_id=test_user_id,
            type="system",
            title=f"n{i}",
        )
    n = await svc.mark_all_read(
        workspace_id=test_workspace_id, user_id=test_user_id
    )
    assert n == 4
    # A second call updates nothing
    assert (
        await svc.mark_all_read(
            workspace_id=test_workspace_id, user_id=test_user_id
        )
        == 0
    )


async def test_mark_all_read_scoped_by_category(
    test_workspace_id: int, test_user_id: int
):
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="video_generated",
        title="p",
    )
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="billing",
        title="b",
    )
    n = await svc.mark_all_read(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        category="pipeline",
    )
    assert n == 1
    # Billing row still unread
    assert (
        await svc.unread_count(
            workspace_id=test_workspace_id, user_id=test_user_id
        )
        == 1
    )


async def test_unread_count_after_create(
    test_workspace_id: int, test_user_id: int
):
    assert (
        await svc.unread_count(
            workspace_id=test_workspace_id, user_id=test_user_id
        )
        == 0
    )
    for _ in range(3):
        await svc.create_notification(
            workspace_id=test_workspace_id,
            user_id=test_user_id,
            type="system",
            title="x",
        )
    assert (
        await svc.unread_count(
            workspace_id=test_workspace_id, user_id=test_user_id
        )
        == 3
    )


async def test_delete_removes_row(test_workspace_id: int, test_user_id: int):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="bye",
    )
    ok = await svc.delete_notification(
        notification_id=row.id,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    assert ok is True
    # Second delete → False
    assert (
        await svc.delete_notification(
            notification_id=row.id,
            workspace_id=test_workspace_id,
            user_id=test_user_id,
        )
        is False
    )


async def test_archive_keeps_row(test_workspace_id: int, test_user_id: int):
    row = await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="archive",
    )
    archived = await svc.archive_notification(
        notification_id=row.id,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    assert archived is not None
    assert archived.archived is True


async def test_fanout_to_users(test_workspace_id: int):
    user_ids = [test_workspace_id + 100, test_workspace_id + 101, test_workspace_id + 102]
    rows = await svc.fanout_to_users(
        workspace_id=test_workspace_id,
        user_ids=user_ids,
        type="template_published",
        title="新模板",
        message="可立即使用",
    )
    assert len(rows) == 3
    assert {r.user_id for r in rows} == set(user_ids)
    assert all(r.category == "pipeline" for r in rows)


async def test_fanout_to_empty_user_list_returns_empty(test_workspace_id: int):
    rows = await svc.fanout_to_users(
        workspace_id=test_workspace_id,
        user_ids=[],
        type="system",
        title="empty",
    )
    assert rows == []


async def test_event_helper_video_generated(
    test_workspace_id: int, test_user_id: int
):
    row = await svc.notify_video_generated(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        task_id="t_001",
        project_id=42,
        duration=15.0,
        preset="social_9x16",
        runtime_seconds=4.2,
    )
    assert row is not None
    assert row.type == "video_generated"
    assert row.payload["task_id"] == "t_001"
    assert row.payload["project_id"] == 42


async def test_event_helper_brand_kit_changed(
    test_workspace_id: int, test_user_id: int
):
    row = await svc.notify_brand_kit_changed(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        kit_id=99,
        kit_name="Acme · Core",
        changed_keys=["primary_color", "font_heading"],
        actor_id=test_user_id,
    )
    assert row is not None
    assert row.category == "drift"
    assert "primary_color" in row.payload["changed_keys"]


async def test_event_helper_swallows_errors(
    test_workspace_id: int, test_user_id: int, monkeypatch
):
    """The ``_swallow`` decorator must never propagate exceptions.

    Mocked failure injected via the underlying create_notification call.
    """
    async def boom(**_kw):
        raise RuntimeError("DB on fire")

    monkeypatch.setattr(svc, "create_notification", boom)
    result = await svc.notify_video_generated(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        task_id="t_001",
        project_id=1,
    )
    assert result is None  # swallowed, no exception raised


async def test_workspace_id_isolation(test_workspace_id: int, test_user_id: int):
    """A notification in workspace X is invisible to workspace Y."""
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="mine",
    )
    other_ws = test_workspace_id + 7777
    items, total, _ = await svc.list_notifications(
        workspace_id=other_ws, user_id=test_user_id
    )
    assert items == []
    assert total == 0


async def test_user_id_isolation(test_workspace_id: int, test_user_id: int):
    """A notification addressed to user A is invisible to user B in the same workspace."""
    user_b = test_user_id + 1
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=test_user_id,
        type="system",
        title="for A",
    )
    items, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=user_b
    )
    assert items == []
    assert total == 0


async def test_workspace_broadcast_visible_to_any_user(
    test_workspace_id: int, test_user_id: int
):
    """Rows with user_id=NULL show up in the workspace-wide read (user_id=None)."""
    await svc.create_notification(
        workspace_id=test_workspace_id,
        user_id=None,
        type="billing",
        title="broadcast",
    )
    items, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=None
    )
    assert total == 1
    assert items[0].user_id is None
