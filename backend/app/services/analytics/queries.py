"""Async SQLAlchemy aggregations for the analytics endpoints.

Every public coroutine here:

* takes an :class:`AsyncSession` first, ``workspace_id`` second, then a
  ``(since, until)`` window — this keeps the call sites uniform and lets
  the aggregator wire them up without thinking about argument order;
* returns plain ``dict`` / ``list[dict]`` (no Pydantic models) — the
  outer aggregator owns the response shape so these stay reusable for
  the CSV/JSON export path;
* uses ``func.coalesce(..., 0)`` for every ``SUM`` and ``AVG`` so empty
  windows return ``0`` instead of ``None``.

The queries are written against the **shared models module** — they do
not own any data themselves and therefore stay healthy whether
``mix_video.py`` is persisting rows (production) or running in-memory
(local demo). Tests seed the DB directly to exercise them.

SQLite caveat: ``func.strftime`` is the bucket projector. PostgreSQL
would prefer ``date_trunc`` but we'd lose the SQLite dev-loop. The bucket
key returned here uses SQLite's Sunday-week numbering; the aggregator
re-formats to ISO weeks via :func:`app.services.analytics.windows.bucket_label`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Asset,
    BrandKit,
    Job,
    Project,
    RenderTask,
    Template,
    User,
    Workspace,
)
from app.schemas.analytics import Granularity
from app.services.analytics.windows import sqlite_strftime_format

# Render-task status enum, mirrored from app.models.render so the queries
# don't drift if a status is added in the future.
_STATUS_SUCCEEDED = "succeeded"
_STATUS_FAILED = "failed"
_STATUS_RUNNING = "running"
_STATUS_QUEUED = "queued"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


async def overview_totals(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
) -> dict[str, int | float]:
    """Single-shot scalar counters used by the dashboard cards.

    Returns a dict with:

    * ``projects_total``       — count(projects) created in window
    * ``projects_active``      — count(projects) status != archived
    * ``renders_total``        — count(render_tasks) queued in window
    * ``renders_succeeded``    — count(render_tasks) status=succeeded
    * ``renders_failed``       — count(render_tasks) status=failed
    * ``renders_running``      — count(render_tasks) status in (running, queued)
    * ``runtime_seconds``      — sum(estimated_seconds) for finished tasks
    * ``avg_runtime_seconds``  — average estimated_seconds over finished tasks
    * ``total_duration_seconds`` — sum(projects.duration_seconds)
    * ``storage_bytes``        — sum(assets.size_bytes) for the workspace

    Using a single SELECT per logical table keeps the round-trip count
    low (3 queries total).
    """
    # Projects in window — also used for distribution downstream.
    projects_stmt = (
        select(
            func.count().label("projects_total"),
            func.coalesce(
                func.sum(
                    # boolean → int via CASE; portable across SQLite + Postgres.
                    _case_when(Project.status != "archived", 1, 0)
                ),
                0,
            ).label("projects_active"),
            func.coalesce(func.sum(Project.duration_seconds), 0).label(
                "total_duration_seconds"
            ),
        )
        .where(
            Project.workspace_id == workspace_id,
            Project.created_at >= since,
            Project.created_at < until,
        )
    )
    projects_row = (await db.execute(projects_stmt)).one()

    # Render tasks — joined back to projects to scope by workspace.
    renders_stmt = (
        select(
            func.count().label("renders_total"),
            func.coalesce(
                func.sum(_case_when(RenderTask.status == _STATUS_SUCCEEDED, 1, 0)),
                0,
            ).label("renders_succeeded"),
            func.coalesce(
                func.sum(_case_when(RenderTask.status == _STATUS_FAILED, 1, 0)),
                0,
            ).label("renders_failed"),
            func.coalesce(
                func.sum(
                    _case_when(
                        RenderTask.status.in_((_STATUS_RUNNING, _STATUS_QUEUED)),
                        1,
                        0,
                    )
                ),
                0,
            ).label("renders_running"),
            func.coalesce(
                func.sum(
                    _case_when(
                        RenderTask.status == _STATUS_SUCCEEDED,
                        RenderTask.estimated_seconds,
                        0.0,
                    )
                ),
                0.0,
            ).label("runtime_seconds"),
            func.coalesce(
                func.avg(
                    _case_when_null(
                        RenderTask.status == _STATUS_SUCCEEDED,
                        RenderTask.estimated_seconds,
                    )
                ),
                0.0,
            ).label("avg_runtime_seconds"),
        )
        .join(Project, RenderTask.project_id == Project.id)
        .where(
            Project.workspace_id == workspace_id,
            RenderTask.queued_at >= since,
            RenderTask.queued_at < until,
        )
    )
    renders_row = (await db.execute(renders_stmt)).one()

    # Storage — independent of window (an asset uploaded yesterday still
    # counts against today's quota), so we don't constrain by date.
    storage_stmt = select(
        func.coalesce(func.sum(Asset.size_bytes), 0).label("storage_bytes")
    ).where(Asset.workspace_id == workspace_id)
    storage_row = (await db.execute(storage_stmt)).one()

    return {
        "projects_total": int(projects_row.projects_total or 0),
        "projects_active": int(projects_row.projects_active or 0),
        "total_duration_seconds": int(projects_row.total_duration_seconds or 0),
        "renders_total": int(renders_row.renders_total or 0),
        "renders_succeeded": int(renders_row.renders_succeeded or 0),
        "renders_failed": int(renders_row.renders_failed or 0),
        "renders_running": int(renders_row.renders_running or 0),
        "runtime_seconds": float(renders_row.runtime_seconds or 0.0),
        "avg_runtime_seconds": float(renders_row.avg_runtime_seconds or 0.0),
        "storage_bytes": int(storage_row.storage_bytes or 0),
    }


async def purpose_distribution(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
) -> list[dict[str, Any]]:
    """Project-count grouped by ``purpose`` for the donut chart."""
    stmt = (
        select(
            Project.purpose,
            func.count().label("value"),
        )
        .where(
            Project.workspace_id == workspace_id,
            Project.created_at >= since,
            Project.created_at < until,
        )
        .group_by(Project.purpose)
        .order_by(func.count().desc())
    )
    rows = (await db.execute(stmt)).all()
    return [{"label": r.purpose, "value": int(r.value)} for r in rows]


async def render_status_distribution(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
) -> list[dict[str, Any]]:
    """Render-task count grouped by status — health-of-pipeline."""
    stmt = (
        select(
            RenderTask.status,
            func.count().label("value"),
        )
        .join(Project, RenderTask.project_id == Project.id)
        .where(
            Project.workspace_id == workspace_id,
            RenderTask.queued_at >= since,
            RenderTask.queued_at < until,
        )
        .group_by(RenderTask.status)
        .order_by(func.count().desc())
    )
    rows = (await db.execute(stmt)).all()
    return [{"label": r.status, "value": int(r.value)} for r in rows]


# ---------------------------------------------------------------------------
# Trends — bucketed time-series
# ---------------------------------------------------------------------------


async def trends_timeseries(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
    granularity: Granularity,
) -> list[dict[str, Any]]:
    """Bucketed render counts + average runtime per bucket.

    Returns rows shaped like::

        {"bucket": "2026-05-22", "rendered": 12, "succeeded": 10,
         "failed": 2, "avg_runtime_seconds": 14.7}

    Empty buckets are filled in by the aggregator (via
    :func:`enumerate_buckets`) — we keep the SQL side honest and only
    emit buckets where at least one row exists.
    """
    fmt = sqlite_strftime_format(granularity)
    bucket_expr = func.strftime(fmt, RenderTask.queued_at).label("bucket")

    stmt = (
        select(
            bucket_expr,
            func.count().label("rendered"),
            func.coalesce(
                func.sum(_case_when(RenderTask.status == _STATUS_SUCCEEDED, 1, 0)),
                0,
            ).label("succeeded"),
            func.coalesce(
                func.sum(_case_when(RenderTask.status == _STATUS_FAILED, 1, 0)),
                0,
            ).label("failed"),
            func.coalesce(
                func.avg(
                    _case_when_null(
                        RenderTask.status == _STATUS_SUCCEEDED,
                        RenderTask.estimated_seconds,
                    )
                ),
                0.0,
            ).label("avg_runtime_seconds"),
        )
        .join(Project, RenderTask.project_id == Project.id)
        .where(
            Project.workspace_id == workspace_id,
            RenderTask.queued_at >= since,
            RenderTask.queued_at < until,
        )
        .group_by("bucket")
        .order_by("bucket")
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "bucket": r.bucket,
            "rendered": int(r.rendered or 0),
            "succeeded": int(r.succeeded or 0),
            "failed": int(r.failed or 0),
            "avg_runtime_seconds": float(r.avg_runtime_seconds or 0.0),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Template usage
# ---------------------------------------------------------------------------


async def template_usage_ranking(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
    limit: int = 10,
) -> tuple[list[dict[str, Any]], int]:
    """Template-usage ranking for projects in the window.

    Templates are referenced from ``Project.config['template']`` (string
    slug, stored by the mix-video pipeline). For SQLite we filter via
    ``json_extract`` — the index is over the JSON column, not the
    extracted key, so it's a sequential scan, but in practice the
    project table stays small enough that this is fine.

    The query joins back to the ``templates`` table to enrich each
    bucket with name and category — falling back to the slug itself if
    no row exists (e.g. for built-in JSON-on-disk templates).

    Returns ``(items, total_uses)`` so the aggregator can compute ``pct``
    without a second round-trip.
    """
    slug_expr = func.json_extract(Project.config, "$.template").label("slug")

    stmt = (
        select(
            slug_expr,
            func.count().label("uses"),
        )
        .where(
            Project.workspace_id == workspace_id,
            Project.created_at >= since,
            Project.created_at < until,
            slug_expr.is_not(None),
        )
        .group_by("slug")
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    # Enrich with template metadata via one extra fetch keyed by slug.
    slugs = [r.slug for r in rows if r.slug]
    meta: dict[str, dict[str, str]] = {}
    if slugs:
        meta_stmt = select(Template.slug, Template.name, Template.category).where(
            Template.slug.in_(slugs)
        )
        for row in (await db.execute(meta_stmt)).all():
            meta[row.slug] = {"name": row.name, "category": row.category}

    items: list[dict[str, Any]] = []
    for r in rows:
        slug = r.slug or "unknown"
        m = meta.get(slug, {})
        items.append(
            {
                "slug": slug,
                "name": m.get("name", slug),
                "category": m.get("category", "uncategorised"),
                "uses": int(r.uses),
            }
        )
    total_uses = sum(item["uses"] for item in items)
    return items, total_uses


# ---------------------------------------------------------------------------
# Brand-kit usage
# ---------------------------------------------------------------------------


async def brand_kit_usage_ranking(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """How many projects in the window referenced each brand kit.

    Brand kits are referenced from ``Project.config['brand_kit_id']``
    (set by the mix-video pipeline when a kit is explicitly applied).
    Kits never referenced still appear in the list — with ``projects=0``
    — so the UI can render the full inventory and not just the popular
    ones. The list is capped at ``limit`` to keep the response bounded.
    """
    kit_id_expr = cast(
        func.json_extract(Project.config, "$.brand_kit_id"), Integer
    ).label("brand_kit_id")

    usage_stmt = (
        select(kit_id_expr, func.count().label("projects"))
        .where(
            Project.workspace_id == workspace_id,
            Project.created_at >= since,
            Project.created_at < until,
            kit_id_expr.is_not(None),
        )
        .group_by("brand_kit_id")
    )
    usage_rows = {
        int(r.brand_kit_id): int(r.projects)
        for r in (await db.execute(usage_stmt)).all()
    }

    kit_stmt = (
        select(BrandKit.id, BrandKit.name, BrandKit.scope, BrandKit.is_active)
        .where(BrandKit.workspace_id == workspace_id)
        .order_by(BrandKit.is_active.desc(), BrandKit.id.asc())
        .limit(limit)
    )
    kit_rows = (await db.execute(kit_stmt)).all()

    out = [
        {
            "brand_kit_id": int(k.id),
            "name": k.name,
            "scope": k.scope,
            "is_active": bool(k.is_active),
            "projects": usage_rows.get(int(k.id), 0),
        }
        for k in kit_rows
    ]
    # Re-rank: kits that were actually used come first.
    out.sort(key=lambda x: (-x["projects"], -int(x["is_active"]), x["brand_kit_id"]))
    return out


# ---------------------------------------------------------------------------
# Team activity
# ---------------------------------------------------------------------------


async def team_activity_ranking(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Active users in the workspace — project & render counts in window."""
    project_counts_stmt = (
        select(
            Project.owner_id.label("user_id"),
            func.count().label("projects"),
        )
        .where(
            Project.workspace_id == workspace_id,
            Project.created_at >= since,
            Project.created_at < until,
        )
        .group_by(Project.owner_id)
    )
    project_counts = {
        int(r.user_id): int(r.projects)
        for r in (await db.execute(project_counts_stmt)).all()
        if r.user_id is not None
    }

    render_counts_stmt = (
        select(
            Project.owner_id.label("user_id"),
            func.count().label("renders"),
            func.max(RenderTask.finished_at).label("last_active_at"),
        )
        .join(Project, RenderTask.project_id == Project.id)
        .where(
            Project.workspace_id == workspace_id,
            RenderTask.queued_at >= since,
            RenderTask.queued_at < until,
        )
        .group_by(Project.owner_id)
    )
    render_counts: dict[int, tuple[int, datetime | None]] = {}
    for r in (await db.execute(render_counts_stmt)).all():
        if r.user_id is not None:
            render_counts[int(r.user_id)] = (int(r.renders), r.last_active_at)

    active_user_ids = set(project_counts) | set(render_counts)
    if not active_user_ids:
        return []
    users_stmt = (
        select(User.id, User.full_name, User.email, User.last_login_at)
        .where(User.id.in_(active_user_ids))
    )
    users = {
        int(u.id): u
        for u in (await db.execute(users_stmt)).all()
    }

    items: list[dict[str, Any]] = []
    for uid in active_user_ids:
        u = users.get(uid)
        if u is None:
            continue
        renders, last_active = render_counts.get(uid, (0, None))
        items.append(
            {
                "user_id": uid,
                "full_name": u.full_name,
                "email": u.email,
                "projects": project_counts.get(uid, 0),
                "renders": renders,
                "last_login_at": u.last_login_at,
                "last_active_at": last_active,
            }
        )
    items.sort(key=lambda x: (-x["renders"], -x["projects"], x["user_id"]))
    return items[:limit]


# ---------------------------------------------------------------------------
# Video stats — per-project drill-down
# ---------------------------------------------------------------------------


async def video_stats(
    db: AsyncSession,
    *,
    workspace_id: int,
    since: datetime,
    until: datetime,
    status: str | None = None,
    purpose: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Per-project render stats with pagination.

    The outer aggregator turns this into ``VideoStatItem`` rows. We do
    the JOIN here in one shot so the (project, render aggregate) tuple
    comes back paginated.

    ``status`` filters at the **project** level (draft/rendering/done/…)
    not at the render-task level — matches the dropdown the frontend
    will surface.
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 200:
        page_size = 200

    filters = [
        Project.workspace_id == workspace_id,
        Project.created_at >= since,
        Project.created_at < until,
    ]
    if status:
        filters.append(Project.status == status)
    if purpose:
        filters.append(Project.purpose == purpose)

    base = select(Project.id).where(and_(*filters))
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

    # The pagination subquery is keyed by Project.id to keep the row
    # count deterministic; we then join render_tasks for aggregates.
    page_stmt = (
        select(Project)
        .where(and_(*filters))
        .order_by(Project.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    projects = (await db.execute(page_stmt)).scalars().all()
    if not projects:
        return [], int(total)

    project_ids = [p.id for p in projects]
    agg_stmt = (
        select(
            RenderTask.project_id.label("project_id"),
            func.count().label("render_count"),
            func.coalesce(
                func.sum(_case_when(RenderTask.status == _STATUS_SUCCEEDED, 1, 0)),
                0,
            ).label("success_count"),
            func.coalesce(
                func.sum(_case_when(RenderTask.status == _STATUS_FAILED, 1, 0)),
                0,
            ).label("failed_count"),
            func.coalesce(func.sum(RenderTask.estimated_seconds), 0.0).label(
                "total_runtime_seconds"
            ),
            func.max(RenderTask.finished_at).label("last_rendered_at"),
        )
        .where(RenderTask.project_id.in_(project_ids))
        .group_by(RenderTask.project_id)
    )
    aggs = {
        int(r.project_id): r for r in (await db.execute(agg_stmt)).all()
    }

    items: list[dict[str, Any]] = []
    for p in projects:
        a = aggs.get(p.id)
        render_count = int(a.render_count) if a else 0
        success_count = int(a.success_count) if a else 0
        failed_count = int(a.failed_count) if a else 0
        success_rate = (success_count / render_count) if render_count else 0.0
        items.append(
            {
                "project_id": p.id,
                "name": p.name,
                "purpose": p.purpose,
                "status": p.status,
                "aspect_ratio": p.aspect_ratio,
                "duration_seconds": int(p.duration_seconds),
                "render_count": render_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "total_runtime_seconds": float(a.total_runtime_seconds) if a else 0.0,
                "success_rate": round(success_rate, 4),
                "last_rendered_at": a.last_rendered_at if a else None,
                "created_at": p.created_at,
            }
        )
    return items, int(total)


# ---------------------------------------------------------------------------
# Workspace sanity / existence check
# ---------------------------------------------------------------------------


async def workspace_exists(db: AsyncSession, workspace_id: int) -> bool:
    """Return True iff the workspace row exists.

    The dashboard endpoint uses this to decide between "real query" and
    "demo fixture" — without it, an unconfigured fresh DB would return
    empty cards that look broken.
    """
    stmt = select(Workspace.id).where(Workspace.id == workspace_id)
    return (await db.execute(stmt)).scalar() is not None


# ---------------------------------------------------------------------------
# Dialect-portable CASE helpers
# ---------------------------------------------------------------------------
#
# SQLAlchemy 2.x's ``case()`` helper changed signature across minor
# versions. To keep the queries readable and version-tolerant we wrap
# the two patterns we actually use into private helpers.


def _case_when(predicate, then_value, else_value):
    """``CASE WHEN predicate THEN then_value ELSE else_value END``."""
    from sqlalchemy import case

    return case((predicate, then_value), else_=else_value)


def _case_when_null(predicate, value):
    """``CASE WHEN predicate THEN value ELSE NULL END`` — for AVG over a subset."""
    from sqlalchemy import case, null

    return case((predicate, value), else_=null())


__all__ = [
    "brand_kit_usage_ranking",
    "overview_totals",
    "purpose_distribution",
    "render_status_distribution",
    "team_activity_ranking",
    "template_usage_ranking",
    "trends_timeseries",
    "video_stats",
    "workspace_exists",
]
