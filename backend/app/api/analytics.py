"""Analytics REST endpoints — the left-rail "数据分析" feature.

Wired against :mod:`app.services.analytics`. The endpoints are deliberately
thin — they validate query params, pull a fresh response from the
aggregator (or the in-memory TTL cache), and serialise. Caching lives at
the API boundary so cache keys naturally include the request's
workspace.

Backward compatibility
~~~~~~~~~~~~~~~~~~~~~~

``GET /analytics/overview`` used to return the demo fixture. The new
implementation returns the live schema by default and serves the legacy
fixture when ``?legacy=true`` is passed — keeps the showcase frontend
working without code changes while the new dashboard is being built out.

Authentication
~~~~~~~~~~~~~~

The workspace id is resolved through :func:`get_current_workspace_id`,
which falls back to ``DEMO_WORKSPACE_ID=1`` for unauthenticated demo
calls. Per-endpoint role checks aren't required — analytics is
**read-only** and the workspace gate already prevents data leaking
across tenants.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_workspace_id, get_db
from app.schemas.analytics import (
    BrandKitsResponse,
    ExportFormat,
    ExportKind,
    Granularity,
    OverviewResponse,
    Period,
    TeamActivityResponse,
    TemplatesResponse,
    TrendsResponse,
    VideosResponse,
)
from app.services.analytics import (
    build_brand_kit_usage,
    build_overview,
    build_team_activity,
    build_template_usage,
    build_trends,
    build_video_stats,
    get_analytics_cache,
)
from app.services.analytics.aggregator import export_rows, legacy_overview_payload
from app.services.analytics.windows import parse_period

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Per-endpoint TTLs. Trends are slower (more buckets) but also less
# urgent — a 5-minute cache feels right; overview is on the dashboard
# and benefits from a tighter 60s.
_TTL_OVERVIEW = 60.0
_TTL_TRENDS = 300.0
_TTL_TEMPLATES = 300.0
_TTL_BRAND_KITS = 300.0
_TTL_TEAM = 120.0
_TTL_VIDEOS = 60.0


def _validate_period(period: str) -> Period:
    """Helper that maps :class:`ValueError` from period parsing to 422."""
    try:
        return parse_period(period)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _cached_response(
    cache_key: tuple[Any, ...],
    response_model: Any,
) -> Any | None:
    """Read the cache; return a fresh ``response_model`` clone with
    ``cached=True`` flipped on, or ``None`` for a cache miss."""
    cached = get_analytics_cache().get(cache_key)
    if cached is None:
        return None
    # The cached payload is a fully-built Pydantic model; cloning lets us
    # flip ``cached`` without mutating the cached instance (so the next
    # request still sees the value as a fresh hit).
    return cached.model_copy(update={"cached": True})


# ---------------------------------------------------------------------------
# /analytics/overview
# ---------------------------------------------------------------------------


@router.get(
    "/overview",
    response_model=None,  # union of legacy dict + OverviewResponse
    summary="Dashboard KPIs + distributions",
)
async def analytics_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    period: str = Query("30d", description="Time window: 7d, 30d, 90d, or all"),
    legacy: bool = Query(False, description="Return the demo fixture instead of live data"),
) -> Any:
    """Return the analytics overview for the current workspace.

    When ``legacy=true`` the historical fixture shape is served instead
    — covers the showcase frontend until it migrates to the new
    schema.
    """
    if legacy:
        return legacy_overview_payload()

    p = _validate_period(period)
    key = ("overview", workspace_id, p)
    hit = _cached_response(key, OverviewResponse)
    if hit is not None:
        return hit

    payload = await build_overview(db, workspace_id=workspace_id, period=p)
    get_analytics_cache().set(key, payload, ttl_seconds=_TTL_OVERVIEW)
    return payload


# ---------------------------------------------------------------------------
# /analytics/trends
# ---------------------------------------------------------------------------


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Bucketed time-series of render activity",
)
async def analytics_trends(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    period: str = Query("30d", description="7d | 30d | 90d | all"),
    granularity: str = Query("day", description="day | week | month"),
) -> TrendsResponse:
    p = _validate_period(period)
    if granularity not in {"day", "week", "month"}:
        raise HTTPException(
            status_code=422,
            detail=f"unknown granularity {granularity!r}; expected day, week, or month",
        )
    g: Granularity = granularity  # type: ignore[assignment]

    key = ("trends", workspace_id, p, g)
    hit = _cached_response(key, TrendsResponse)
    if hit is not None:
        return hit

    payload = await build_trends(
        db, workspace_id=workspace_id, period=p, granularity=g
    )
    get_analytics_cache().set(key, payload, ttl_seconds=_TTL_TRENDS)
    return payload


# ---------------------------------------------------------------------------
# /analytics/templates
# ---------------------------------------------------------------------------


@router.get(
    "/templates",
    response_model=TemplatesResponse,
    summary="Template usage ranking",
)
async def analytics_templates(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    period: str = Query("30d"),
    limit: int = Query(10, ge=1, le=100),
) -> TemplatesResponse:
    p = _validate_period(period)
    key = ("templates", workspace_id, p, limit)
    hit = _cached_response(key, TemplatesResponse)
    if hit is not None:
        return hit
    payload = await build_template_usage(
        db, workspace_id=workspace_id, period=p, limit=limit
    )
    get_analytics_cache().set(key, payload, ttl_seconds=_TTL_TEMPLATES)
    return payload


# ---------------------------------------------------------------------------
# /analytics/brand-kits
# ---------------------------------------------------------------------------


@router.get(
    "/brand-kits",
    response_model=BrandKitsResponse,
    summary="Brand-kit usage ranking",
)
async def analytics_brand_kits(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    period: str = Query("30d"),
    limit: int = Query(10, ge=1, le=100),
) -> BrandKitsResponse:
    p = _validate_period(period)
    key = ("brand-kits", workspace_id, p, limit)
    hit = _cached_response(key, BrandKitsResponse)
    if hit is not None:
        return hit
    payload = await build_brand_kit_usage(
        db, workspace_id=workspace_id, period=p, limit=limit
    )
    get_analytics_cache().set(key, payload, ttl_seconds=_TTL_BRAND_KITS)
    return payload


# ---------------------------------------------------------------------------
# /analytics/team
# ---------------------------------------------------------------------------


@router.get(
    "/team",
    response_model=TeamActivityResponse,
    summary="Per-user activity (projects + renders) in window",
)
async def analytics_team(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    period: str = Query("30d"),
    limit: int = Query(20, ge=1, le=200),
) -> TeamActivityResponse:
    p = _validate_period(period)
    key = ("team", workspace_id, p, limit)
    hit = _cached_response(key, TeamActivityResponse)
    if hit is not None:
        return hit
    payload = await build_team_activity(
        db, workspace_id=workspace_id, period=p, limit=limit
    )
    get_analytics_cache().set(key, payload, ttl_seconds=_TTL_TEAM)
    return payload


# ---------------------------------------------------------------------------
# /analytics/videos
# ---------------------------------------------------------------------------


@router.get(
    "/videos",
    response_model=VideosResponse,
    summary="Per-project render aggregates (paginated)",
)
async def analytics_videos(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    period: str = Query("30d"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = Query(
        default=None,
        description="Filter by project status (draft, scripting, rendering, review, done, archived)",
    ),
    purpose: str | None = Query(
        default=None,
        description="Filter by project purpose (marketing, training, product_demo, social)",
    ),
) -> VideosResponse:
    p = _validate_period(period)
    # ``status`` and ``purpose`` are part of the cache key so filtered
    # views don't collide with the unfiltered baseline.
    key = ("videos", workspace_id, p, page, page_size, status or "", purpose or "")
    hit = _cached_response(key, VideosResponse)
    if hit is not None:
        return hit
    payload = await build_video_stats(
        db,
        workspace_id=workspace_id,
        period=p,
        status=status,
        purpose=purpose,
        page=page,
        page_size=page_size,
    )
    get_analytics_cache().set(key, payload, ttl_seconds=_TTL_VIDEOS)
    return payload


# ---------------------------------------------------------------------------
# /analytics/export
# ---------------------------------------------------------------------------


@router.get(
    "/export",
    summary="Export analytics rows as CSV or JSON",
    responses={
        200: {
            "content": {
                "text/csv": {},
                "application/json": {},
            },
            "description": "Downloadable export file",
        }
    },
)
async def analytics_export(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    kind: str = Query("videos", description="overview | trends | templates | videos"),
    period: str = Query("30d"),
    fmt: str = Query("csv", description="csv | json", alias="format"),
    granularity: str = Query("day", description="day | week | month (only used for kind=trends)"),
) -> Response:
    """Download the underlying rows for a chart as CSV or JSON.

    Exports are **never cached** — they're typically pulled once and the
    cost of regenerating is dominated by serialisation, not aggregation
    (the live queries are still cached one level down).
    """
    if kind not in {"overview", "trends", "templates", "videos"}:
        raise HTTPException(
            status_code=422,
            detail=f"unknown kind {kind!r}; expected overview, trends, templates, or videos",
        )
    if fmt not in {"csv", "json"}:
        raise HTTPException(
            status_code=422,
            detail=f"unknown format {fmt!r}; expected csv or json",
        )
    if granularity not in {"day", "week", "month"}:
        raise HTTPException(
            status_code=422,
            detail=f"unknown granularity {granularity!r}",
        )
    p = _validate_period(period)
    k: ExportKind = kind  # type: ignore[assignment]
    f: ExportFormat = fmt  # type: ignore[assignment]
    g: Granularity = granularity  # type: ignore[assignment]

    body, media_type, filename = await export_rows(
        db,
        workspace_id=workspace_id,
        kind=k,
        period=p,
        fmt=f,
        granularity=g,
    )
    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Generated-At": datetime.utcnow().isoformat(),
        },
    )


__all__ = ["router"]
