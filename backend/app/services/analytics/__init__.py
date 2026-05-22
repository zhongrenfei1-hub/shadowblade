"""Analytics service — SQL aggregation + in-memory TTL cache.

The module is intentionally split so each unit has a single responsibility:

* :mod:`.windows` — period parsing, prior-window math, bucket labels.
* :mod:`.cache`   — process-local TTL cache (Redis-ready interface).
* :mod:`.queries` — async SQLAlchemy queries against Job / RenderTask /
  Project / Template / BrandKit / Asset.
* :mod:`.aggregator` — orchestrator that composes the response payloads
  consumed by :mod:`app.api.analytics`.

Public surface is re-exported here so callers can write::

    from app.services.analytics import build_overview
"""

from app.services.analytics.aggregator import (
    build_brand_kit_usage,
    build_overview,
    build_team_activity,
    build_template_usage,
    build_trends,
    build_video_stats,
    export_rows,
)
from app.services.analytics.cache import TTLCache, get_analytics_cache
from app.services.analytics.windows import (
    bucket_label,
    parse_period,
    period_window,
    previous_window,
)

__all__ = [
    "TTLCache",
    "bucket_label",
    "build_brand_kit_usage",
    "build_overview",
    "build_team_activity",
    "build_template_usage",
    "build_trends",
    "build_video_stats",
    "export_rows",
    "get_analytics_cache",
    "parse_period",
    "period_window",
    "previous_window",
]
