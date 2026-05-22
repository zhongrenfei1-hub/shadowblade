"""Notification service — write path, read path, and event hooks.

Layered the way the fastapi-fullstack-template separates *core CRUD* from
*business event helpers*:

* :func:`create_notification`, :func:`list_notifications`,
  :func:`mark_read`, :func:`mark_all_read`, :func:`delete_notification`
  and :func:`unread_count` are the raw CRUD primitives the REST router
  calls.

* :func:`notify_video_generated`, :func:`notify_video_failed`,
  :func:`notify_template_updated`, :func:`notify_template_published`,
  :func:`notify_team_invite`, :func:`notify_team_member_joined`,
  :func:`notify_brand_kit_changed`, :func:`notify_brand_drift_detected`,
  :func:`notify_mention`, :func:`notify_approval_requested`,
  :func:`notify_approval_granted`, :func:`notify_billing` are the high-
  level "an event happened, write the right notification" hooks the rest
  of the codebase pulls in.

The trigger helpers all accept an *optional* :class:`AsyncSession`. When
called from a background task (which has its own short-lived session) they
take a session in; when called as a fire-and-forget background helper from
a request handler they open their own session via ``SessionLocal``. Either
mode commits before returning so the caller never has to.

We deliberately do **not** raise on bad inputs — these run on the success
path of mix-video / brand-kit / template / team mutations and must never
take the parent request down. Failures are logged via
``shadowblade.notifications`` and swallowed.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.models.notification import (
    NOTIFICATION_CATEGORIES,
    NOTIFICATION_KINDS,
    NOTIFICATION_TYPES,
    Notification,
)

log = logging.getLogger("shadowblade.notifications")


# Mapping: type → (category, default kind). Single source of truth so the
# trigger helpers and the categorisation logic can't drift. Kept here
# rather than on the model so the model file stays a pure schema artifact.
TYPE_CATEGORY: dict[str, str] = {
    "video_generated": "pipeline",
    "video_failed": "pipeline",
    "template_updated": "pipeline",
    "template_published": "pipeline",
    "team_invite": "system",
    "team_member_joined": "system",
    "brand_kit_changed": "drift",
    "brand_drift_detected": "drift",
    "mention": "mentions",
    "approval_requested": "approvals",
    "approval_granted": "approvals",
    "billing": "billing",
    "system": "system",
}

TYPE_DEFAULT_KIND: dict[str, str] = {
    "video_generated": "done",
    "video_failed": "fail",
    "template_updated": "info",
    "template_published": "info",
    "team_invite": "info",
    "team_member_joined": "done",
    "brand_kit_changed": "info",
    "brand_drift_detected": "warn",
    "mention": "mention",
    "approval_requested": "info",
    "approval_granted": "done",
    "billing": "billing",
    "system": "info",
}


# ---------------------------------------------------------------------------
# Session helper
# ---------------------------------------------------------------------------


class _SessionContext:
    """Use the provided session if non-None, else open a fresh SessionLocal.

    Lets every helper accept ``db: AsyncSession | None`` so background
    tasks can pass their own session (avoiding the connection storm a
    burst of notifications would otherwise create) without forcing all
    callers to manage that.
    """

    def __init__(self, db: AsyncSession | None):
        self._given = db
        self._opened: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        if self._given is not None:
            return self._given
        self._opened = SessionLocal()
        return self._opened

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._opened is not None:
            await self._opened.close()
            self._opened = None


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def _normalise_type(value: str) -> str:
    """Validate ``value`` against the closed enum; raise ValueError if not.

    The Pydantic layer already enforces this for public API calls, but the
    internal trigger helpers bypass schemas, so we re-check here.
    """
    if value not in NOTIFICATION_TYPES:
        raise ValueError(
            f"unknown notification type {value!r}; expected one of {NOTIFICATION_TYPES}"
        )
    return value


def _derive_category(ntype: str, override: str | None) -> str:
    if override:
        if override not in NOTIFICATION_CATEGORIES:
            raise ValueError(f"unknown category {override!r}")
        return override
    return TYPE_CATEGORY.get(ntype, "system")


def _derive_kind(ntype: str, override: str | None) -> str:
    if override:
        if override not in NOTIFICATION_KINDS:
            raise ValueError(f"unknown kind {override!r}")
        return override
    return TYPE_DEFAULT_KIND.get(ntype, "info")


async def create_notification(
    *,
    workspace_id: int,
    user_id: int | None,
    type: str,
    title: str,
    message: str = "",
    payload: dict | None = None,
    category: str | None = None,
    kind: str | None = None,
    db: AsyncSession | None = None,
) -> Notification:
    """Insert a single notification row.

    Returns the freshly-refreshed ORM object so the caller can read the
    generated ``id`` / ``created_at``. Commits before returning.
    """
    type_ = _normalise_type(type)
    cat = _derive_category(type_, category)
    knd = _derive_kind(type_, kind)
    row = Notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type=type_,
        category=cat,
        kind=knd,
        title=title,
        message=message or "",
        payload=payload or {},
        read=False,
        archived=False,
    )
    async with _SessionContext(db) as session:
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def fanout_to_users(
    *,
    workspace_id: int,
    user_ids: Iterable[int],
    type: str,
    title: str,
    message: str = "",
    payload: dict | None = None,
    category: str | None = None,
    kind: str | None = None,
    db: AsyncSession | None = None,
) -> list[Notification]:
    """Fan a single event out to many users in one transaction.

    Used when an org-wide event (template published, brand kit changed)
    should land in every active member's inbox. Avoids the per-user
    session churn that calling :func:`create_notification` in a loop would
    incur.
    """
    type_ = _normalise_type(type)
    cat = _derive_category(type_, category)
    knd = _derive_kind(type_, kind)
    rows = [
        Notification(
            workspace_id=workspace_id,
            user_id=uid,
            type=type_,
            category=cat,
            kind=knd,
            title=title,
            message=message or "",
            payload=payload or {},
            read=False,
            archived=False,
        )
        for uid in user_ids
    ]
    if not rows:
        return []
    async with _SessionContext(db) as session:
        session.add_all(rows)
        await session.commit()
        for row in rows:
            await session.refresh(row)
    return rows


async def list_notifications(
    *,
    workspace_id: int,
    user_id: int | None,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    category: str | None = None,
    type: str | None = None,
    include_archived: bool = False,
    db: AsyncSession | None = None,
) -> tuple[list[Notification], int, int]:
    """Read notifications for the caller, plus the global counts.

    Returns ``(items, total, unread)`` so the frontend can render a tab-
    counted inbox without a second round-trip. ``user_id=None`` means
    *workspace-wide broadcast view* — admins/owners use this to peek at
    what's been delivered across the org.
    """
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    base = select(Notification).where(Notification.workspace_id == workspace_id)
    if user_id is not None:
        base = base.where(Notification.user_id == user_id)
    if not include_archived:
        base = base.where(Notification.archived.is_(False))
    if unread_only:
        base = base.where(Notification.read.is_(False))
    if category:
        if category not in NOTIFICATION_CATEGORIES:
            raise ValueError(f"unknown category {category!r}")
        base = base.where(Notification.category == category)
    if type:
        if type not in NOTIFICATION_TYPES:
            raise ValueError(f"unknown type {type!r}")
        base = base.where(Notification.type == type)

    # Counts use a separate query so pagination doesn't distort them.
    total_stmt = select(func.count()).select_from(base.subquery())
    unread_stmt = select(func.count()).where(
        Notification.workspace_id == workspace_id,
        Notification.read.is_(False),
        Notification.archived.is_(False),
    )
    if user_id is not None:
        unread_stmt = unread_stmt.where(Notification.user_id == user_id)

    page = (
        base.order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
    )

    async with _SessionContext(db) as session:
        items = (await session.execute(page)).scalars().all()
        total = int((await session.execute(total_stmt)).scalar() or 0)
        unread = int((await session.execute(unread_stmt)).scalar() or 0)

    return list(items), total, unread


async def unread_count(
    *,
    workspace_id: int,
    user_id: int | None,
    db: AsyncSession | None = None,
) -> int:
    stmt = select(func.count()).where(
        Notification.workspace_id == workspace_id,
        Notification.read.is_(False),
        Notification.archived.is_(False),
    )
    if user_id is not None:
        stmt = stmt.where(Notification.user_id == user_id)
    async with _SessionContext(db) as session:
        return int((await session.execute(stmt)).scalar() or 0)


async def mark_read(
    *,
    notification_id: int,
    workspace_id: int,
    user_id: int | None,
    db: AsyncSession | None = None,
) -> Notification | None:
    """Flip a single row to read=True. Returns None if not found / not owned."""
    async with _SessionContext(db) as session:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == workspace_id,
        )
        if user_id is not None:
            stmt = stmt.where(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )
        row = (await session.execute(stmt)).scalars().first()
        if row is None:
            return None
        if not row.read:
            row.read = True
            row.read_at = datetime.utcnow()
            await session.commit()
            await session.refresh(row)
        return row


async def mark_all_read(
    *,
    workspace_id: int,
    user_id: int | None,
    category: str | None = None,
    db: AsyncSession | None = None,
) -> int:
    """Flip every unread row matching the filter to read=True.

    Returns the number of rows updated so the API can confirm to the UI.
    """
    stmt = (
        update(Notification)
        .where(
            Notification.workspace_id == workspace_id,
            Notification.read.is_(False),
            Notification.archived.is_(False),
        )
        .values(read=True, read_at=datetime.utcnow())
    )
    if user_id is not None:
        stmt = stmt.where(Notification.user_id == user_id)
    if category:
        if category not in NOTIFICATION_CATEGORIES:
            raise ValueError(f"unknown category {category!r}")
        stmt = stmt.where(Notification.category == category)

    async with _SessionContext(db) as session:
        result = await session.execute(stmt)
        await session.commit()
        return int(result.rowcount or 0)


async def delete_notification(
    *,
    notification_id: int,
    workspace_id: int,
    user_id: int | None,
    db: AsyncSession | None = None,
) -> bool:
    """Hard-delete one row. Returns True iff a row was removed.

    The frontend has both a "dismiss" (soft-archive) and a "delete"
    (hard-remove) gesture. This implements the latter; soft-archive lives
    on :func:`archive_notification` below.
    """
    stmt = delete(Notification).where(
        Notification.id == notification_id,
        Notification.workspace_id == workspace_id,
    )
    if user_id is not None:
        stmt = stmt.where(
            (Notification.user_id == user_id) | (Notification.user_id.is_(None))
        )
    async with _SessionContext(db) as session:
        result = await session.execute(stmt)
        await session.commit()
        return bool(result.rowcount and result.rowcount > 0)


async def archive_notification(
    *,
    notification_id: int,
    workspace_id: int,
    user_id: int | None,
    db: AsyncSession | None = None,
) -> Notification | None:
    """Soft-archive (sets ``archived=True``); row still exists for audit."""
    async with _SessionContext(db) as session:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.workspace_id == workspace_id,
        )
        if user_id is not None:
            stmt = stmt.where(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )
        row = (await session.execute(stmt)).scalars().first()
        if row is None:
            return None
        if not row.archived:
            row.archived = True
            await session.commit()
            await session.refresh(row)
        return row


# ---------------------------------------------------------------------------
# Event helpers — used by mix-video / brand_kits / templates / team flows
# ---------------------------------------------------------------------------


def _swallow(coro_name: str):
    """Decorator that swallows + logs exceptions so trigger helpers never
    crash the calling request.

    Notifications are best-effort. If the DB hiccups on a notification
    write the user should still get their render result back.
    """

    def deco(fn):
        async def wrapper(*args, **kwargs):
            try:
                return await fn(*args, **kwargs)
            except Exception:  # noqa: BLE001 — best-effort by design
                log.exception("notification trigger %s failed", coro_name)
                return None

        wrapper.__name__ = fn.__name__
        wrapper.__doc__ = fn.__doc__
        return wrapper

    return deco


@_swallow("notify_video_generated")
async def notify_video_generated(
    *,
    workspace_id: int,
    user_id: int | None,
    task_id: str,
    project_id: int | str,
    duration: float | None = None,
    preset: str | None = None,
    output_path: str | None = None,
    runtime_seconds: float | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    """Fired by ``api.mix_video`` once a render task completes."""
    title = f"视频生成完成 · #{project_id}"
    bits = []
    if duration is not None:
        bits.append(f"时长 {duration:.1f}s")
    if preset:
        bits.append(f"预设 {preset}")
    if runtime_seconds is not None:
        bits.append(f"渲染 {runtime_seconds:.1f}s")
    msg = " · ".join(bits) if bits else "渲染已就绪，可下载或继续编辑。"
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="video_generated",
        title=title,
        message=msg,
        payload={
            "task_id": task_id,
            "project_id": project_id,
            "duration": duration,
            "preset": preset,
            "output_path": output_path,
            "runtime_seconds": runtime_seconds,
        },
        db=db,
    )


@_swallow("notify_video_failed")
async def notify_video_failed(
    *,
    workspace_id: int,
    user_id: int | None,
    task_id: str,
    project_id: int | str,
    error: str,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="video_failed",
        title=f"视频生成失败 · #{project_id}",
        message=error[:1000],
        payload={"task_id": task_id, "project_id": project_id, "error": error},
        db=db,
    )


@_swallow("notify_template_updated")
async def notify_template_updated(
    *,
    workspace_id: int,
    user_id: int | None,
    template_name: str,
    changed_keys: list[str] | None = None,
    actor_id: int | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    changes = ", ".join(changed_keys or []) or "细节调整"
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="template_updated",
        title=f"模板已更新 · {template_name}",
        message=f"变更字段：{changes}",
        payload={
            "template_name": template_name,
            "changed_keys": changed_keys or [],
            "actor_id": actor_id,
        },
        db=db,
    )


@_swallow("notify_template_published")
async def notify_template_published(
    *,
    workspace_id: int,
    user_id: int | None,
    template_name: str,
    category: str | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="template_published",
        title=f"新模板已发布 · {template_name}",
        message=f"分类：{category or '未分类'}，立即可用。",
        payload={"template_name": template_name, "category": category},
        db=db,
    )


@_swallow("notify_team_invite")
async def notify_team_invite(
    *,
    workspace_id: int,
    user_id: int | None,
    email: str,
    role: str = "member",
    invited_by: int | None = None,
    invite_code: str | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="team_invite",
        title=f"已邀请 {email}",
        message=f"角色 {role}，等待对方接受。",
        payload={
            "email": email,
            "role": role,
            "invited_by": invited_by,
            "invite_code": invite_code,
        },
        db=db,
    )


@_swallow("notify_team_member_joined")
async def notify_team_member_joined(
    *,
    workspace_id: int,
    user_id: int | None,
    new_member_email: str,
    new_member_id: int | None = None,
    role: str = "member",
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="team_member_joined",
        title=f"新成员加入 · {new_member_email}",
        message=f"角色 {role}，已获取访问权限。",
        payload={
            "new_member_email": new_member_email,
            "new_member_id": new_member_id,
            "role": role,
        },
        db=db,
    )


@_swallow("notify_brand_kit_changed")
async def notify_brand_kit_changed(
    *,
    workspace_id: int,
    user_id: int | None,
    kit_id: int,
    kit_name: str,
    changed_keys: list[str] | None = None,
    actor_id: int | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    changes = ", ".join(changed_keys or []) or "默认值"
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="brand_kit_changed",
        title=f"品牌套件已更新 · {kit_name}",
        message=f"变更字段：{changes}",
        payload={
            "kit_id": kit_id,
            "kit_name": kit_name,
            "changed_keys": changed_keys or [],
            "actor_id": actor_id,
        },
        db=db,
    )


@_swallow("notify_brand_drift_detected")
async def notify_brand_drift_detected(
    *,
    workspace_id: int,
    user_id: int | None,
    project_id: int | str,
    drift_count: int,
    sample_field: str | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="brand_drift_detected",
        title=f"检测到品牌偏移 · {drift_count} 条",
        message=(f"示例字段：{sample_field}" if sample_field else "建议一键修复"),
        payload={
            "project_id": project_id,
            "drift_count": drift_count,
            "sample_field": sample_field,
        },
        db=db,
    )


@_swallow("notify_mention")
async def notify_mention(
    *,
    workspace_id: int,
    user_id: int,
    actor_name: str,
    snippet: str,
    project_id: int | str | None = None,
    thread_id: str | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="mention",
        title=f"{actor_name} @ 了你",
        message=snippet[:500],
        payload={
            "actor_name": actor_name,
            "project_id": project_id,
            "thread_id": thread_id,
        },
        db=db,
    )


@_swallow("notify_approval_requested")
async def notify_approval_requested(
    *,
    workspace_id: int,
    user_id: int,
    project_id: int | str,
    requested_by: str,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="approval_requested",
        title="新的审批请求",
        message=f"{requested_by} 请求你审批项目 #{project_id}",
        payload={"project_id": project_id, "requested_by": requested_by},
        db=db,
    )


@_swallow("notify_approval_granted")
async def notify_approval_granted(
    *,
    workspace_id: int,
    user_id: int,
    project_id: int | str,
    approver_name: str,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="approval_granted",
        title=f"审批通过 · 项目 #{project_id}",
        message=f"{approver_name} 已批准。",
        payload={"project_id": project_id, "approver_name": approver_name},
        db=db,
    )


@_swallow("notify_billing")
async def notify_billing(
    *,
    workspace_id: int,
    user_id: int | None,
    title: str,
    message: str,
    payload: dict | None = None,
    db: AsyncSession | None = None,
) -> Notification | None:
    return await create_notification(
        workspace_id=workspace_id,
        user_id=user_id,
        type="billing",
        title=title,
        message=message,
        payload=payload or {},
        db=db,
    )


__all__ = [
    "TYPE_CATEGORY",
    "TYPE_DEFAULT_KIND",
    "archive_notification",
    "create_notification",
    "delete_notification",
    "fanout_to_users",
    "list_notifications",
    "mark_all_read",
    "mark_read",
    "notify_approval_granted",
    "notify_approval_requested",
    "notify_billing",
    "notify_brand_drift_detected",
    "notify_brand_kit_changed",
    "notify_mention",
    "notify_team_invite",
    "notify_team_member_joined",
    "notify_template_published",
    "notify_template_updated",
    "notify_video_failed",
    "notify_video_generated",
    "unread_count",
]
