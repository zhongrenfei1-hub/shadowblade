"""Orchestrator that composes query results into endpoint responses.

The aggregator is responsible for:

* turning SQL row dicts into Pydantic schemas (re-using the ones in
  :mod:`app.schemas.analytics`);
* computing **derived** metrics that the SQL layer doesn't try to do —
  period-over-period deltas, ratio-of-total percentages, success rate;
* filling **empty buckets** in the trend series so the chart doesn't
  show gaps;
* re-formatting SQLite's Sunday-week labels into ISO weeks so the
  frontend can render them as ``2026-W21`` rather than ``2026-W20``
  (Sunday-vs-Monday delta);
* falling back to the legacy fixture when the workspace has no data —
  this is what keeps the design ring working out of the box.

Every public coroutine returns a fully-built Pydantic model so the API
layer stays thin.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    BrandKitsResponse,
    BrandKitUsageItem,
    BucketCount,
    ExportFormat,
    ExportKind,
    Granularity,
    OverviewKPI,
    OverviewResponse,
    Period,
    TeamActivityItem,
    TeamActivityResponse,
    TemplatesResponse,
    TemplateUsageItem,
    TrendPoint,
    TrendsResponse,
    VideosResponse,
    VideoStatItem,
)
from app.services.analytics import queries
from app.services.analytics.windows import (
    bucket_label,
    enumerate_buckets,
    is_empty_window,
    period_window,
    previous_window,
)
from app.services.fixtures import analytics_fixture

# Minimum number of records required before we trust the live data over
# the demo fixture. Without this threshold a freshly-bootstrapped DB
# (one project, zero renders) returns near-empty charts and the
# dashboard looks broken.
_LIVE_DATA_THRESHOLD = 1


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


async def build_overview(
    db: AsyncSession,
    *,
    workspace_id: int,
    period: Period,
    now: datetime | None = None,
) -> OverviewResponse:
    """Assemble :class:`OverviewResponse` — KPIs + distributions + totals.

    ``period`` controls the rolling window for **everything except**
    storage_bytes, which is workspace-wide on principle (it doesn't make
    sense to "ignore" assets older than 30 days for a quota indicator).
    """
    since, until = period_window(period, now=now)
    totals = await queries.overview_totals(
        db, workspace_id=workspace_id, since=since, until=until
    )

    # Prior window for deltas — skip when the period is all-time.
    prior_totals: dict[str, int | float] = {}
    if not is_empty_window(*previous_window(since, until)):
        p_since, p_until = previous_window(since, until)
        prior_totals = await queries.overview_totals(
            db, workspace_id=workspace_id, since=p_since, until=p_until
        )

    distribution = await queries.purpose_distribution(
        db, workspace_id=workspace_id, since=since, until=until
    )
    status_dist = await queries.render_status_distribution(
        db, workspace_id=workspace_id, since=since, until=until
    )

    kpis = _build_kpis(totals, prior_totals)

    return OverviewResponse.model_validate(
        {
            "workspace_id": workspace_id,
            "period": period,
            "generated_at": datetime.utcnow(),
            "from": since,
            "to": until,
            "cached": False,
            "kpis": kpis,
            "distribution": [BucketCount.model_validate(d) for d in distribution],
            "status_distribution": [
                BucketCount.model_validate(d) for d in status_dist
            ],
            "totals": totals,
        }
    )


def _build_kpis(
    totals: dict[str, int | float],
    prior: dict[str, int | float],
) -> list[OverviewKPI]:
    """Translate raw counters into the dashboard's KPI cards."""

    def delta(curr_key: str, prior_key: str | None = None) -> float | None:
        if not prior:
            return None
        p = prior.get(prior_key or curr_key, 0) or 0
        c = totals.get(curr_key, 0) or 0
        if not p:
            return None  # avoid divide-by-zero — UI renders as "—"
        return round((c - p) / p, 4)

    renders_total = int(totals.get("renders_total", 0))
    renders_succeeded = int(totals.get("renders_succeeded", 0))
    success_rate = (renders_succeeded / renders_total) if renders_total else 0.0

    prior_renders_total = int(prior.get("renders_total", 0)) if prior else 0
    prior_renders_succeeded = int(prior.get("renders_succeeded", 0)) if prior else 0
    prior_success_rate = (
        prior_renders_succeeded / prior_renders_total if prior_renders_total else 0.0
    )
    success_delta: float | None = None
    if prior and prior_renders_total:
        success_delta = round(success_rate - prior_success_rate, 4)

    return [
        OverviewKPI(
            key="videos_total",
            label="本期视频总数",
            value=float(totals.get("projects_total", 0)),
            unit="count",
            delta=delta("projects_total"),
        ),
        OverviewKPI(
            key="renders_total",
            label="渲染次数",
            value=float(renders_total),
            unit="count",
            delta=delta("renders_total"),
        ),
        OverviewKPI(
            key="success_rate",
            label="渲染成功率",
            value=round(success_rate, 4),
            unit="ratio",
            delta=success_delta,
        ),
        OverviewKPI(
            key="avg_runtime_seconds",
            label="平均生成时长",
            value=round(float(totals.get("avg_runtime_seconds", 0.0)), 2),
            unit="seconds",
            delta=delta("avg_runtime_seconds"),
        ),
        OverviewKPI(
            key="total_runtime_seconds",
            label="累计生成时长",
            value=round(float(totals.get("runtime_seconds", 0.0)), 2),
            unit="seconds",
            delta=delta("runtime_seconds"),
        ),
        OverviewKPI(
            key="storage_bytes",
            label="素材存储用量",
            value=float(totals.get("storage_bytes", 0)),
            unit="bytes",
            delta=None,  # workspace-wide; deltas are meaningless here
        ),
    ]


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------


async def build_trends(
    db: AsyncSession,
    *,
    workspace_id: int,
    period: Period,
    granularity: Granularity,
    now: datetime | None = None,
) -> TrendsResponse:
    """Bucketed time-series response."""
    since, until = period_window(period, now=now)
    raw = await queries.trends_timeseries(
        db,
        workspace_id=workspace_id,
        since=since,
        until=until,
        granularity=granularity,
    )

    # SQLite's strftime("%Y-W%W", ...) uses Sunday-based weeks; convert
    # each bucket to the ISO-week label we already use elsewhere so
    # ``2026-W21`` lines up between this endpoint and any python-side
    # bucket math.
    rebucketed: dict[str, dict[str, Any]] = {}
    for row in raw:
        if granularity == "week":
            # Re-derive the ISO key by parsing the SQL bucket back to a
            # date (Sunday of that week) and asking ``bucket_label`` for
            # the ISO version.
            try:
                year, week = row["bucket"].split("-W")
                # Sunday of SQLite week N of year Y in Python:
                #   datetime.strptime(f"{Y} {N} 0", "%Y %W %w")
                anchor = datetime.strptime(f"{year} {week} 0", "%Y %W %w")
                row = {**row, "bucket": bucket_label(anchor, "week")}
            except (ValueError, IndexError):
                # Malformed bucket — keep the raw label so we don't drop data.
                pass
        rebucketed.setdefault(row["bucket"], row)

    # Fill empty buckets so the chart shows a continuous series.
    out: list[TrendPoint] = []
    for label in enumerate_buckets(since, until, granularity):
        row = rebucketed.get(label)
        if row is None:
            out.append(
                TrendPoint(
                    bucket=label,
                    rendered=0,
                    succeeded=0,
                    failed=0,
                    avg_runtime_seconds=0.0,
                )
            )
        else:
            out.append(
                TrendPoint(
                    bucket=row["bucket"],
                    rendered=row["rendered"],
                    succeeded=row["succeeded"],
                    failed=row["failed"],
                    avg_runtime_seconds=round(row["avg_runtime_seconds"], 2),
                )
            )

    return TrendsResponse.model_validate(
        {
            "workspace_id": workspace_id,
            "period": period,
            "generated_at": datetime.utcnow(),
            "from": since,
            "to": until,
            "cached": False,
            "granularity": granularity,
            "points": out,
        }
    )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


async def build_template_usage(
    db: AsyncSession,
    *,
    workspace_id: int,
    period: Period,
    limit: int = 10,
    now: datetime | None = None,
) -> TemplatesResponse:
    """Template usage ranking."""
    since, until = period_window(period, now=now)
    rows, total_uses = await queries.template_usage_ranking(
        db, workspace_id=workspace_id, since=since, until=until, limit=limit
    )
    items = [
        TemplateUsageItem(
            slug=r["slug"],
            name=r["name"],
            category=r["category"],
            uses=r["uses"],
            pct=round(r["uses"] / total_uses, 4) if total_uses else 0.0,
        )
        for r in rows
    ]
    return TemplatesResponse.model_validate(
        {
            "workspace_id": workspace_id,
            "period": period,
            "generated_at": datetime.utcnow(),
            "from": since,
            "to": until,
            "cached": False,
            "total_uses": total_uses,
            "items": items,
        }
    )


# ---------------------------------------------------------------------------
# Brand-kit usage
# ---------------------------------------------------------------------------


async def build_brand_kit_usage(
    db: AsyncSession,
    *,
    workspace_id: int,
    period: Period,
    limit: int = 10,
    now: datetime | None = None,
) -> BrandKitsResponse:
    since, until = period_window(period, now=now)
    rows = await queries.brand_kit_usage_ranking(
        db, workspace_id=workspace_id, since=since, until=until, limit=limit
    )
    items = [BrandKitUsageItem.model_validate(r) for r in rows]
    return BrandKitsResponse.model_validate(
        {
            "workspace_id": workspace_id,
            "period": period,
            "generated_at": datetime.utcnow(),
            "from": since,
            "to": until,
            "cached": False,
            "total": len(items),
            "items": items,
        }
    )


# ---------------------------------------------------------------------------
# Team activity
# ---------------------------------------------------------------------------


async def build_team_activity(
    db: AsyncSession,
    *,
    workspace_id: int,
    period: Period,
    limit: int = 20,
    now: datetime | None = None,
) -> TeamActivityResponse:
    since, until = period_window(period, now=now)
    rows = await queries.team_activity_ranking(
        db, workspace_id=workspace_id, since=since, until=until, limit=limit
    )
    items = [TeamActivityItem.model_validate(r) for r in rows]
    return TeamActivityResponse.model_validate(
        {
            "workspace_id": workspace_id,
            "period": period,
            "generated_at": datetime.utcnow(),
            "from": since,
            "to": until,
            "cached": False,
            "total": len(items),
            "items": items,
        }
    )


# ---------------------------------------------------------------------------
# Videos
# ---------------------------------------------------------------------------


async def build_video_stats(
    db: AsyncSession,
    *,
    workspace_id: int,
    period: Period,
    status: str | None = None,
    purpose: str | None = None,
    page: int = 1,
    page_size: int = 20,
    now: datetime | None = None,
) -> VideosResponse:
    since, until = period_window(period, now=now)
    items, total = await queries.video_stats(
        db,
        workspace_id=workspace_id,
        since=since,
        until=until,
        status=status,
        purpose=purpose,
        page=page,
        page_size=page_size,
    )
    return VideosResponse.model_validate(
        {
            "workspace_id": workspace_id,
            "period": period,
            "generated_at": datetime.utcnow(),
            "from": since,
            "to": until,
            "cached": False,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [VideoStatItem.model_validate(it) for it in items],
        }
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


async def export_rows(
    db: AsyncSession,
    *,
    workspace_id: int,
    kind: ExportKind,
    period: Period,
    fmt: ExportFormat,
    granularity: Granularity = "day",
    now: datetime | None = None,
) -> tuple[bytes, str, str]:
    """Render an export payload + its content-type + suggested filename.

    Returns a ``(bytes, media_type, filename)`` tuple so the endpoint can
    plug it straight into :class:`fastapi.responses.Response` without
    knowing about CSV plumbing.
    """
    if kind == "overview":
        data = await build_overview(db, workspace_id=workspace_id, period=period, now=now)
        rows: list[dict[str, Any]] = [k.model_dump() for k in data.kpis]
    elif kind == "trends":
        data = await build_trends(
            db,
            workspace_id=workspace_id,
            period=period,
            granularity=granularity,
            now=now,
        )
        rows = [p.model_dump() for p in data.points]
    elif kind == "templates":
        data = await build_template_usage(
            db, workspace_id=workspace_id, period=period, now=now
        )
        rows = [it.model_dump() for it in data.items]
    elif kind == "videos":
        data = await build_video_stats(
            db,
            workspace_id=workspace_id,
            period=period,
            page=1,
            page_size=200,
            now=now,
        )
        rows = [it.model_dump() for it in data.items]
    else:  # pragma: no cover — validated upstream
        raise ValueError(f"unknown export kind: {kind}")

    filename = f"analytics-{kind}-{period}.{fmt}"
    if fmt == "json":
        body = json.dumps(
            {
                "kind": kind,
                "period": period,
                "workspace_id": workspace_id,
                "exported_at": datetime.utcnow().isoformat(),
                "rows": rows,
            },
            ensure_ascii=False,
            default=str,
            indent=2,
        ).encode("utf-8")
        return body, "application/json", filename

    # CSV
    if not rows:
        return b"", "text/csv", filename
    buf = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: _csv_safe(v) for k, v in r.items()})
    return buf.getvalue().encode("utf-8"), "text/csv", filename


def _csv_safe(value: Any) -> Any:
    """Stringify exotic types (datetime, dict, list) for CSV cells."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


# ---------------------------------------------------------------------------
# Fixture fallback (legacy compat)
# ---------------------------------------------------------------------------


def legacy_overview_payload() -> dict[str, Any]:
    """Return the shape the old ``/analytics/overview`` returned.

    The original endpoint shipped a fixture; the new one returns a much
    richer schema. We expose this helper so the API layer can serve the
    legacy shape (under ``?legacy=true``) without re-implementing the
    formatting in two places.
    """
    return analytics_fixture()


__all__ = [
    "build_brand_kit_usage",
    "build_overview",
    "build_team_activity",
    "build_template_usage",
    "build_trends",
    "build_video_stats",
    "export_rows",
    "legacy_overview_payload",
]
