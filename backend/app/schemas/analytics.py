"""Analytics response schemas.

Modelled after fastapi/full-stack-fastapi-template conventions:

* `*Read` / `*Item` for atoms;
* `*Response` envelopes for every endpoint so the frontend gets metadata
  (period, generated_at, workspace_id) alongside the payload — never bare
  arrays.

The shapes are intentionally backward-compatible with the legacy
``analytics_fixture()`` payload (``kpis`` + ``timeseries`` + ``distribution``)
so the existing frontend chart components keep rendering while the new
endpoints are wired in.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Period = Literal["7d", "30d", "90d", "all"]
Granularity = Literal["day", "week", "month"]
KPIUnit = Literal["count", "minutes", "seconds", "ratio", "bytes", "usd"]
ExportFormat = Literal["csv", "json"]
ExportKind = Literal["videos", "trends", "templates", "overview"]


# ---------------------------------------------------------------------------
# Atoms
# ---------------------------------------------------------------------------


class OverviewKPI(BaseModel):
    """One headline KPI card on the dashboard.

    ``delta`` is the period-over-period ratio compared to the immediately
    preceding window of the same length (None when the prior window has no
    data, which the UI renders as a neutral ``—``).
    """

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="Stable identifier; chart links join on this")
    label: str = Field(..., description="Localised display label")
    value: float = Field(..., description="Raw numeric value in its unit")
    unit: KPIUnit
    delta: float | None = Field(
        default=None,
        description="Period-over-period ratio (e.g. 0.12 = +12%); None when undefined",
    )


class BucketCount(BaseModel):
    """One slice of a categorical distribution (e.g. purpose, status)."""

    model_config = ConfigDict(extra="forbid")

    label: str
    value: int


class TrendPoint(BaseModel):
    """One bucket of a time-series (day / ISO-week / month).

    All counters are non-negative integers; ``avg_runtime_seconds`` is the
    weighted average over the finished render tasks in this bucket and is
    ``0.0`` if no task finished.
    """

    model_config = ConfigDict(extra="forbid")

    bucket: str = Field(..., description="ISO date for day, YYYY-Www for week, YYYY-MM for month")
    rendered: int = Field(0, ge=0, description="render_tasks queued in window")
    succeeded: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
    avg_runtime_seconds: float = Field(0.0, ge=0.0)


class TemplateUsageItem(BaseModel):
    """One row in the template-usage ranking."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    category: str
    uses: int = Field(..., ge=0)
    pct: float = Field(..., ge=0.0, le=1.0, description="uses / total_uses")


class BrandKitUsageItem(BaseModel):
    """One row in the brand-kit-usage ranking."""

    model_config = ConfigDict(extra="forbid")

    brand_kit_id: int
    name: str
    scope: str
    is_active: bool
    projects: int = Field(..., ge=0)


class TeamActivityItem(BaseModel):
    """One row in the team activity table."""

    model_config = ConfigDict(extra="forbid")

    user_id: int
    full_name: str
    email: str
    projects: int = Field(..., ge=0)
    renders: int = Field(..., ge=0)
    last_login_at: datetime | None = None
    last_active_at: datetime | None = None


class VideoStatItem(BaseModel):
    """Aggregated stats for a single project (one row in the videos table)."""

    model_config = ConfigDict(extra="forbid")

    project_id: int
    name: str
    purpose: str
    status: str
    aspect_ratio: str
    duration_seconds: int
    render_count: int = Field(..., ge=0)
    success_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    total_runtime_seconds: float = Field(..., ge=0.0)
    success_rate: float = Field(..., ge=0.0, le=1.0)
    last_rendered_at: datetime | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


class _AnalyticsEnvelope(BaseModel):
    """Common metadata wrapper inherited by every response."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: int
    period: Period
    generated_at: datetime
    from_: datetime = Field(..., alias="from")
    to: datetime
    cached: bool = Field(default=False, description="True when served from in-memory cache")


class OverviewResponse(_AnalyticsEnvelope):
    """The dashboard's headline section."""

    kpis: list[OverviewKPI]
    distribution: list[BucketCount] = Field(
        default_factory=list,
        description="Project distribution by purpose",
    )
    status_distribution: list[BucketCount] = Field(
        default_factory=list,
        description="Render task distribution by status",
    )
    totals: dict[str, int | float] = Field(
        default_factory=dict,
        description="Raw counters (videos, renders, succeeded, failed, runtime_seconds)",
    )


class TrendsResponse(_AnalyticsEnvelope):
    granularity: Granularity
    points: list[TrendPoint]


class TemplatesResponse(_AnalyticsEnvelope):
    total_uses: int = Field(..., ge=0)
    items: list[TemplateUsageItem]


class BrandKitsResponse(_AnalyticsEnvelope):
    total: int = Field(..., ge=0)
    items: list[BrandKitUsageItem]


class TeamActivityResponse(_AnalyticsEnvelope):
    total: int = Field(..., ge=0)
    items: list[TeamActivityItem]


class VideosResponse(_AnalyticsEnvelope):
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=200)
    items: list[VideoStatItem]


__all__ = [
    "BrandKitUsageItem",
    "BrandKitsResponse",
    "BucketCount",
    "ExportFormat",
    "ExportKind",
    "Granularity",
    "OverviewKPI",
    "OverviewResponse",
    "Period",
    "TeamActivityItem",
    "TeamActivityResponse",
    "TemplatesResponse",
    "TemplateUsageItem",
    "TrendPoint",
    "TrendsResponse",
    "VideoStatItem",
    "VideosResponse",
]
