"""Demo seed — inject realistic notifications for workspace id=1.

Lets the React `/(app)/notifications` page light up immediately on a
fresh database without manually exercising every trigger path. Mirrors
the rhythm and voice of the existing frontend mock (see
``frontend-next/app/(app)/notifications/page.tsx``):

* covers all six categories (pipeline / approvals / mentions / drift /
  billing / system) so each tab has at least one row;
* mixes ``done`` / ``warn`` / ``fail`` / ``info`` / ``mention`` /
  ``billing`` kinds so the UI's six-color palette is exercised;
* leaves the last few notifications unread so the unread badge isn't
  zero out of the gate;
* writes through the public ``notify_*`` helpers (not raw INSERT) so the
  payload shape stays in lockstep with the production trigger paths —
  if a helper signature changes, this seed breaks the test suite and we
  catch it.

Run:

    cd backend && .venv/bin/python -m app.services.notifications_demo
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import delete

from app.core.db import SessionLocal
from app.models.notification import Notification
from app.services import notifications as svc

log = logging.getLogger("shadowblade.notifications.demo")


async def _wipe_demo_rows(workspace_id: int) -> int:
    """Drop every notification in the demo workspace so reseeding is idempotent."""
    async with SessionLocal() as session:
        result = await session.execute(
            delete(Notification).where(Notification.workspace_id == workspace_id)
        )
        await session.commit()
        return int(result.rowcount or 0)


async def _set_created_at(
    notification: Notification | None, when: datetime
) -> None:
    """Override the auto-stamped ``created_at`` so the seed has realistic spacing.

    The trigger helpers always stamp ``func.now()`` on insert; for a demo we
    want the rows to look like they accumulated over hours/days, not all in
    the same second. Done with a small UPDATE per row so we don't have to
    bypass the helper layer.
    """
    if notification is None:
        return
    async with SessionLocal() as session:
        row = await session.get(Notification, notification.id)
        if row is None:
            return
        row.created_at = when
        await session.commit()


async def _mark_some_read(workspace_id: int, leave_unread: int = 5) -> None:
    """Mark older rows read so the unread badge reads a realistic number.

    Keeps the ``leave_unread`` most recent rows in the unread state, marks
    everything older as read. Mirrors how a returning user's inbox looks.
    """
    from sqlalchemy import select, update

    async with SessionLocal() as session:
        ids = (
            await session.execute(
                select(Notification.id)
                .where(Notification.workspace_id == workspace_id)
                .order_by(Notification.created_at.desc())
            )
        ).scalars().all()
        to_mark = list(ids)[leave_unread:]
        if not to_mark:
            return
        await session.execute(
            update(Notification)
            .where(Notification.id.in_(to_mark))
            .values(read=True, read_at=datetime.utcnow())
        )
        await session.commit()


async def seed_demo_notifications(
    workspace_id: int = 1, user_id: int = 1
) -> int:
    """Reseed the demo workspace's notifications inbox.

    Returns the number of rows inserted.
    """
    deleted = await _wipe_demo_rows(workspace_id)
    log.info("demo seed: cleared %s existing rows", deleted)

    now = datetime.utcnow()
    inserted: list[Notification | None] = []

    # ---- pipeline (run finished, run started, run failed) ----
    inserted.append(
        await svc.notify_video_generated(
            workspace_id=workspace_id,
            user_id=user_id,
            task_id="tsk_8f3a91",
            project_id=901,
            duration=23.4,
            preset="social-9x16",
            output_path="/static/storage/mix/job_901/preview.mp4",
            runtime_seconds=338.0,
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(minutes=1))

    inserted.append(
        await svc.notify_video_generated(
            workspace_id=workspace_id,
            user_id=user_id,
            task_id="tsk_4d2b1c",
            project_id=902,
            duration=18.7,
            preset="social-1x1",
            runtime_seconds=142.0,
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(minutes=9))

    inserted.append(
        await svc.notify_video_failed(
            workspace_id=workspace_id,
            user_id=user_id,
            task_id="tsk_5e7f22",
            project_id=903,
            error="素材源 timeout: archive.org 30s 内未返回 — 已自动重排队。",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(hours=2))

    inserted.append(
        await svc.notify_template_published(
            workspace_id=workspace_id,
            user_id=user_id,
            template_name="618 大促开场",
            category="electronics",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(hours=6))

    # ---- mentions ----
    inserted.append(
        await svc.notify_mention(
            workspace_id=workspace_id,
            user_id=user_id,
            actor_name="Priya Rao",
            snippet="帮看看新片尾？上轮在 TikTok 转化高了约 22%。",
            project_id=901,
            thread_id="thr_a8f2",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(minutes=3))

    inserted.append(
        await svc.notify_mention(
            workspace_id=workspace_id,
            user_id=user_id,
            actor_name="Marcus Lee",
            snippet="字幕 CPS 6.2，能再短点吗？现在节奏稍急。",
            project_id=901,
            thread_id="thr_b9c1",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(hours=1))

    # ---- drift (品牌偏移 / 套件变更) ----
    inserted.append(
        await svc.notify_brand_drift_detected(
            workspace_id=workspace_id,
            user_id=user_id,
            project_id=904,
            drift_count=2,
            sample_field="primary_color",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(minutes=22))

    inserted.append(
        await svc.notify_brand_kit_changed(
            workspace_id=workspace_id,
            user_id=user_id,
            kit_id=1,
            kit_name="Core",
            changed_keys=["logo_url", "watermark_position"],
            actor_id=user_id,
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(hours=4))

    # ---- approvals ----
    inserted.append(
        await svc.notify_approval_requested(
            workspace_id=workspace_id,
            user_id=user_id,
            project_id=905,
            requested_by="Marcus Lee",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(minutes=44))

    inserted.append(
        await svc.notify_approval_granted(
            workspace_id=workspace_id,
            user_id=user_id,
            project_id=898,
            approver_name="Priya Rao",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(hours=8))

    # ---- billing ----
    inserted.append(
        await svc.notify_billing(
            workspace_id=workspace_id,
            user_id=user_id,
            title="UTC 零点结算",
            message="本周期已用 387 / 1,000 条渲染。无超额预警。",
            payload={"used": 387, "quota": 1000, "period": "2026-05W3"},
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(hours=5))

    inserted.append(
        await svc.notify_billing(
            workspace_id=workspace_id,
            user_id=user_id,
            title="存储用量提醒 · 已用 72%",
            message="storage/mix/ 占用 14.4 GB / 20 GB，可点击清理过期成片。",
            payload={"used_gb": 14.4, "quota_gb": 20.0, "bucket": "mix"},
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(days=1))

    # ---- system (team invite / member joined) ----
    inserted.append(
        await svc.notify_team_member_joined(
            workspace_id=workspace_id,
            user_id=user_id,
            new_member_email="ling.chen@acme.co",
            new_member_id=42,
            role="reviewer",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(hours=3))

    inserted.append(
        await svc.notify_team_invite(
            workspace_id=workspace_id,
            user_id=user_id,
            email="kai.zhou@partner.io",
            role="member",
            invited_by=user_id,
            invite_code="inv_3kf9wq",
        )
    )
    await _set_created_at(inserted[-1], now - timedelta(days=2))

    # Mark older rows as read so the unread badge reads ~5 (matches the
    # React mock's "5 未读" first impression).
    await _mark_some_read(workspace_id=workspace_id, leave_unread=5)

    successful = [n for n in inserted if n is not None]
    log.info("demo seed: inserted %s notifications", len(successful))
    return len(successful)


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    count = await seed_demo_notifications(workspace_id=1, user_id=1)
    print(f"OK · 已写入 {count} 条 demo 通知到 workspace_id=1")
    print("查看：curl -H 'X-Workspace-Id: 1' -H 'X-User-Id: 1' "
          "http://localhost:8000/api/v1/notifications")


if __name__ == "__main__":
    asyncio.run(_main())
