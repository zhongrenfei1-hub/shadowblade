"""GET /api/v1/workbench/* — the Studio Workbench aggregate endpoints.

The Workbench is the operator-facing landing surface inside the "Studio /
Production" pillar. It is the place where someone who just opened the app
should be able to:

* see today's headline numbers (renders done, queue depth, success rate)
* spot what's currently rendering and how far along it is
* re-open one of their recent projects in one click
* pick a template and jump straight into ``mix-video``
* know which Brand Kit will be folded into the next render

This module deliberately does *not* expose new persistence — every value it
returns is derived from existing first-class resources (``Project``, ``Job``,
``RenderTask``, ``BrandKit``, the in-memory ``_TASKS`` registry from the
mix-video module, and the template loader). That keeps it a pure read-model:
no schema migration, no double-writes, no drift between Workbench numbers
and the rest of the app.

Endpoints
---------

``GET /api/v1/workbench/overview``
    KPI tiles + active brand kit + featured templates + quick-action wiring.
    Drives the dashboard hero row.

``GET /api/v1/workbench/recent-projects``
    Last-N projects ordered by ``updated_at`` desc, scoped to the caller's
    workspace. Each entry carries the data the Studio sidebar needs to
    render a card without a second round-trip.

``GET /api/v1/workbench/active-tasks``
    Currently running and recently finished mix-video renders, merged from
    the in-memory ``_TASKS`` registry *and* the ``RenderTask`` ORM rows so
    the UI shows one coherent timeline regardless of where the work runs.

All three are GET-only — the Workbench *triggers* work by handing the user
off to the existing ``POST /mix-video`` flow, never by writing new state.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user_id,
    get_current_workspace_id,
    get_db,
)
from app.models.brand_kit import BrandKit as BrandKitORM
from app.models.job import Job
from app.models.project import Project
from app.models.render import RenderTask

log = logging.getLogger("shadowblade.api.workbench")
router = APIRouter(prefix="/workbench", tags=["workbench"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    """UTC clock — pulled out so tests can monkey-patch it deterministically."""
    return datetime.now(timezone.utc)


def _start_of_today_utc() -> datetime:
    """Midnight UTC for the current day — used to scope 'today's renders'."""
    now = _now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _iso(dt: datetime | None) -> str | None:
    """Render a datetime as an ISO-8601 string with TZ, or None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def _resolve_active_brand_kit(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int | None,
) -> BrandKitORM | None:
    """Same resolution order as :func:`mix_video._load_active_brand_kit`.

    Duplicated here (instead of imported) so the Workbench endpoints stay
    decoupled from the mix-video module's import-time side effects (which
    pulls in the heavy ``MixPipeline`` graph). Behaviour MUST stay aligned —
    if the resolution order changes there, mirror it here so the Workbench
    always shows the kit that will actually be applied.
    """
    if user_id is not None:
        stmt = (
            select(BrandKitORM)
            .where(
                BrandKitORM.workspace_id == workspace_id,
                BrandKitORM.scope == "user",
                BrandKitORM.owner_id == user_id,
                BrandKitORM.is_active.is_(True),
            )
            .order_by(BrandKitORM.id.desc())
            .limit(1)
        )
        result = (await db.execute(stmt)).scalars().first()
        if result is not None:
            return result

    stmt = (
        select(BrandKitORM)
        .where(
            BrandKitORM.workspace_id == workspace_id,
            BrandKitORM.scope == "workspace",
            BrandKitORM.is_active.is_(True),
        )
        .order_by(BrandKitORM.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


def _serialize_brand_kit(kit: BrandKitORM | None) -> dict[str, Any] | None:
    """Trim a BrandKit row to the fields the Workbench surface actually shows."""
    if kit is None:
        return None
    return {
        "id": kit.id,
        "name": kit.name or "默认品牌",
        "scope": kit.scope,
        "primary_color": kit.primary_color,
        "accent_color": kit.accent_color,
        "secondary_color": kit.secondary_color,
        "font_heading": kit.font_heading,
        "font_body": kit.font_body,
        "logo_url": kit.logo_url,
        "voice": kit.voice,
        "watermark_position": kit.watermark_position,
        "is_active": bool(kit.is_active),
    }


def _serialize_project_card(p: Project) -> dict[str, Any]:
    """One project row shaped exactly the way the Workbench card expects.

    Includes ``href_open`` so the frontend can wire a 'Open in Studio' link
    without hard-coding URL shape per page.
    """
    return {
        "id": p.id,
        "name": p.name,
        "purpose": p.purpose,
        "status": p.status,
        "aspect_ratio": p.aspect_ratio,
        "duration_seconds": p.duration_seconds,
        "voice": p.voice,
        "brief": (p.brief[:160] + "…") if p.brief and len(p.brief) > 160 else (p.brief or ""),
        "cover_url": p.cover_url,
        "updated_at": _iso(p.updated_at),
        "created_at": _iso(p.created_at),
        "href_open": f"/studio.html?project={p.id}",
        "href_detail": f"/project-detail.html?id={p.id}",
    }


# ---------------------------------------------------------------------------
# Mix-video task registry bridge
# ---------------------------------------------------------------------------


def _live_mix_tasks(project_ids: set[int | str] | None = None) -> list[dict[str, Any]]:
    """Snapshot the in-memory ``_TASKS`` dict from the mix-video module.

    Filtered by ``project_ids`` when provided so cross-workspace tasks don't
    leak into another tenant's Workbench. ``project_ids`` accepts ``int`` or
    ``str`` because mix-video allows free-form project ids in its payload.

    Lazy-imported to keep the module-load graph small and to avoid a circular
    import — ``mix_video`` itself does not depend on this module.
    """
    from app.api.mix_video import _TASKS

    items: list[dict[str, Any]] = []
    for task_id, payload in _TASKS.items():
        if project_ids is not None:
            pid = payload.get("project_id")
            # Match both numeric and string forms so a payload using
            # project_id=101 matches a workspace listing of [101].
            if pid not in project_ids and str(pid) not in {str(x) for x in project_ids}:
                continue
        items.append(
            {
                "task_id": task_id,
                "source": "mix_video",
                "status": payload.get("status", "queued"),
                "progress": float(payload.get("progress") or 0.0),
                "project_id": payload.get("project_id"),
                "preset": payload.get("preset"),
                "duration": payload.get("duration"),
                "runtime_seconds": payload.get("runtime_seconds"),
                "output_path": payload.get("output_path"),
                "cover_path": payload.get("cover_path"),
                "error": payload.get("error"),
            }
        )
    return items


# ---------------------------------------------------------------------------
# GET /workbench/overview
# ---------------------------------------------------------------------------


@router.get("/overview")
async def overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Top-of-page Workbench summary — KPI tiles, brand kit, quick actions.

    Returns a single JSON document so the frontend can render the entire
    dashboard hero with one HTTP round-trip.
    """
    workspace_projects = (
        await db.execute(
            select(Project.id).where(Project.workspace_id == workspace_id)
        )
    ).scalars().all()
    workspace_project_ids: set[int | str] = set(workspace_projects)

    # --- KPI tiles -----------------------------------------------------------
    today_start = _start_of_today_utc()
    week_start = today_start - timedelta(days=6)

    # Today's renders — completed RenderTask rows scoped to this workspace.
    if workspace_project_ids:
        renders_today_stmt = (
            select(func.count(RenderTask.id))
            .where(
                RenderTask.project_id.in_(workspace_project_ids),
                RenderTask.status == "succeeded",
                RenderTask.finished_at >= today_start,
            )
        )
        renders_today = int((await db.execute(renders_today_stmt)).scalar() or 0)

        renders_week_stmt = (
            select(func.count(RenderTask.id))
            .where(
                RenderTask.project_id.in_(workspace_project_ids),
                RenderTask.status == "succeeded",
                RenderTask.finished_at >= week_start,
            )
        )
        renders_week = int((await db.execute(renders_week_stmt)).scalar() or 0)

        in_progress_stmt = (
            select(func.count(RenderTask.id))
            .where(
                RenderTask.project_id.in_(workspace_project_ids),
                RenderTask.status.in_(("queued", "running")),
            )
        )
        in_progress_db = int((await db.execute(in_progress_stmt)).scalar() or 0)
    else:
        renders_today = renders_week = in_progress_db = 0

    # Also fold in live mix-video tasks (in-memory, not yet persisted to DB).
    live_tasks = _live_mix_tasks(workspace_project_ids or None)
    in_progress_live = sum(1 for t in live_tasks if t["status"] in ("queued", "running"))
    succeeded_today_live = sum(
        1 for t in live_tasks if t["status"] == "succeeded"
    )

    total_projects = int(
        (
            await db.execute(
                select(func.count(Project.id)).where(
                    Project.workspace_id == workspace_id
                )
            )
        ).scalar()
        or 0
    )

    # --- Featured templates ---------------------------------------------------
    # Lazy import so the heavy template loader (which scans the on-disk
    # templates directory) only runs when the overview is requested.
    from app.services.template import list_templates

    featured: list[dict[str, Any]] = []
    try:
        for summary in list_templates():
            featured.append(
                {
                    "name": summary.name,
                    "version": summary.version,
                    "description": summary.description,
                    "tags": list(summary.tags),
                    "builtin": summary.builtin,
                    "href": f"/new-video.html?template={summary.name}",
                }
            )
    except Exception:  # noqa: BLE001 — never let template IO 500 the dashboard
        log.exception("workbench overview: failed to list templates")

    # Sort: builtin first (they're the curated path), then by name for stability.
    featured.sort(key=lambda t: (not t["builtin"], t["name"]))
    featured = featured[:6]

    # --- Brand Kit ------------------------------------------------------------
    kit = await _resolve_active_brand_kit(
        db, workspace_id=workspace_id, user_id=user_id
    )
    brand_kit = _serialize_brand_kit(kit)

    # --- Quick action wiring (frontend reads `endpoint` so it never
    #     hard-codes the URL).
    quick_actions = [
        {
            "key": "new_video",
            "label": "新建视频",
            "description": "选择模板，立刻进入制作流程",
            "endpoint": "/api/v1/mix-video",
            "method": "POST",
            "href": "/new-video.html",
        },
        {
            "key": "preview_video",
            "label": "快速预览",
            "description": "360p 同步预览，60 秒以内",
            "endpoint": "/api/v1/mix-video/preview",
            "method": "POST",
            "href": "/new-video.html?mode=preview",
        },
        {
            "key": "upload_asset",
            "label": "上传素材",
            "description": "把镜头、配音、字幕加入素材库",
            "endpoint": "/api/v1/assets",
            "method": "POST",
            "href": "/assets.html",
        },
        {
            "key": "browse_templates",
            "label": "浏览模板",
            "description": "按用途与画幅挑选模板",
            "endpoint": "/api/v1/templates",
            "method": "GET",
            "href": "/templates.html",
        },
    ]

    return {
        "workspace_id": workspace_id,
        "generated_at": _iso(_now()),
        "kpis": [
            {
                "key": "renders_today",
                "label": "今日已渲染",
                "value": renders_today + succeeded_today_live,
                "unit": "videos",
            },
            {
                "key": "renders_this_week",
                "label": "本周已渲染",
                "value": renders_week,
                "unit": "videos",
            },
            {
                "key": "in_progress",
                "label": "进行中任务",
                "value": in_progress_db + in_progress_live,
                "unit": "tasks",
            },
            {
                "key": "total_projects",
                "label": "项目总数",
                "value": total_projects,
                "unit": "projects",
            },
        ],
        "brand_kit": brand_kit,
        "featured_templates": featured,
        "quick_actions": quick_actions,
    }


# ---------------------------------------------------------------------------
# GET /workbench/recent-projects
# ---------------------------------------------------------------------------


@router.get("/recent-projects")
async def recent_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    limit: int = Query(default=8, ge=1, le=24),
):
    """Most-recently-updated projects for the current workspace.

    Sorted by ``updated_at`` desc so the Workbench shows the file you were
    just working on at the top. ``limit`` is bounded so a misconfigured
    client cannot DOS the dashboard by asking for thousands of rows.
    """
    stmt = (
        select(Project)
        .where(Project.workspace_id == workspace_id)
        .order_by(desc(Project.updated_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "items": [_serialize_project_card(p) for p in rows],
        "total": len(rows),
        "workspace_id": workspace_id,
        "limit": limit,
    }


# ---------------------------------------------------------------------------
# GET /workbench/active-tasks
# ---------------------------------------------------------------------------


@router.get("/active-tasks")
async def active_tasks(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    include_recent_succeeded: bool = Query(
        default=True,
        description=(
            "When True, recently-succeeded mix-video tasks are included so "
            "the UI can show a 'just finished' row before it auto-clears."
        ),
    ),
):
    """Currently running tasks merged from RenderTask (DB) + mix-video memory.

    Two sources are unioned because they represent the *same workflow* at
    different stages of maturity:

    * ``RenderTask`` rows persist across restarts and feed the analytics
      dashboard.
    * The in-memory ``_TASKS`` dict from :mod:`app.api.mix_video` holds
      requests that are still running in this process and have not yet
      reached the persistence layer.

    Without the merge the UI would either miss in-flight work (DB-only) or
    miss historical jobs (memory-only). The frontend renders the union with
    ``source`` labelling them so users can tell live work apart from queue.
    """
    workspace_project_ids = set(
        (
            await db.execute(
                select(Project.id).where(Project.workspace_id == workspace_id)
            )
        ).scalars().all()
    )

    db_items: list[dict[str, Any]] = []
    if workspace_project_ids:
        statuses = ("queued", "running")
        stmt = (
            select(RenderTask)
            .where(
                RenderTask.project_id.in_(workspace_project_ids),
                RenderTask.status.in_(statuses),
            )
            .order_by(desc(RenderTask.queued_at))
            .limit(25)
        )
        rows = (await db.execute(stmt)).scalars().all()

        # Resolve project names in a single follow-up query so the card can
        # show "正在渲染：春季产品发布" instead of a bare id.
        project_name_map: dict[int, str] = {}
        if rows:
            project_ids = {r.project_id for r in rows}
            name_stmt = select(Project.id, Project.name).where(
                Project.id.in_(project_ids)
            )
            for pid, name in (await db.execute(name_stmt)).all():
                project_name_map[pid] = name

        for r in rows:
            db_items.append(
                {
                    "task_id": f"render-{r.id}",
                    "source": "render_queue",
                    "project_id": r.project_id,
                    "project_name": project_name_map.get(r.project_id, f"项目 #{r.project_id}"),
                    "status": r.status,
                    "progress": r.progress,
                    "priority": r.priority,
                    "estimated_seconds": r.estimated_seconds,
                    "worker": r.worker,
                    "output_url": r.output_url,
                    "queued_at": _iso(r.queued_at),
                    "started_at": _iso(r.started_at),
                    "finished_at": _iso(r.finished_at),
                }
            )

    live_raw = _live_mix_tasks(workspace_project_ids or None)
    live_items: list[dict[str, Any]] = []
    for t in live_raw:
        if not include_recent_succeeded and t["status"] == "succeeded":
            continue
        if t["status"] == "failed":
            # Always include failures so the user can act on them.
            pass
        live_items.append(t)

    # Most active first — running before queued before succeeded/failed.
    _priority = {"running": 0, "queued": 1, "succeeded": 2, "failed": 3}
    merged = sorted(
        db_items + live_items,
        key=lambda t: (_priority.get(t.get("status"), 9), -float(t.get("progress") or 0.0)),
    )

    return {
        "workspace_id": workspace_id,
        "generated_at": _iso(_now()),
        "items": merged,
        "total": len(merged),
        "sources": {
            "render_queue": len(db_items),
            "mix_video": len(live_items),
        },
    }


__all__ = ["router"]
