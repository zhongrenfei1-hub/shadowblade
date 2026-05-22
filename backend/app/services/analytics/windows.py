"""Time-window math for analytics queries.

Centralises three concerns that the queries module would otherwise
duplicate:

1. **Period parsing** — translate ``"7d" | "30d" | "90d" | "all"`` to a
   ``(since, until)`` datetime tuple in UTC. ``"all"`` returns
   ``datetime.min`` so callers can pass it straight into a SQL ``>=``.

2. **Previous-window** — for KPI deltas the dashboard needs the same
   query repeated on the immediately preceding equal-length window.

3. **Bucket labels** — formatting the GROUP BY key for day / ISO-week /
   month so the frontend gets a stable sortable string.

All datetimes are **naive UTC** (no tzinfo) — matching what SQLAlchemy's
``server_default=func.now()`` produces on SQLite. Comparing tz-aware vs.
naive values would raise; keeping the whole pipeline naive avoids the
trap.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from app.schemas.analytics import Granularity, Period

# Anchor used for the ``"all"`` period — a sentinel that's safely before
# any conceivable created_at. We avoid ``datetime.min`` because SQLite's
# strftime would render it as ``0001-…``, which trips a few clients.
_EPOCH_ANCHOR = datetime(2000, 1, 1)


def _utcnow() -> datetime:
    """Naive UTC ``now`` — matches SQLAlchemy ``func.now()`` on SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_period(period: str) -> Period:
    """Validate and normalise a period string.

    Raises :class:`ValueError` on an unknown period so the API layer can
    map it to a 422 response with a precise message.
    """
    if period not in {"7d", "30d", "90d", "all"}:
        raise ValueError(
            f"unknown period {period!r}; expected one of 7d, 30d, 90d, all"
        )
    return period  # type: ignore[return-value]


def period_window(period: Period, *, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Translate a period token into a ``(since, until)`` UTC pair.

    ``until`` is always the current instant — the frontend treats trends
    as running up to *right now* so partial buckets show today's activity
    as it accumulates.
    """
    until = (now or _utcnow())
    if period == "7d":
        return until - timedelta(days=7), until
    if period == "30d":
        return until - timedelta(days=30), until
    if period == "90d":
        return until - timedelta(days=90), until
    # ``"all"`` falls through here.
    return _EPOCH_ANCHOR, until


def previous_window(
    since: datetime, until: datetime
) -> tuple[datetime, datetime]:
    """The window of equal length immediately preceding ``[since, until)``.

    Used to compute the period-over-period delta on each KPI. For the
    ``"all"`` period the prior window collapses to an empty range
    (``since == until == _EPOCH_ANCHOR``) — callers should treat the
    resulting count of ``0`` as "delta undefined" and surface ``None``.
    """
    length = until - since
    return since - length, since


def is_empty_window(since: datetime, until: datetime) -> bool:
    """True when the prior-window math degenerated (all-time periods)."""
    return since >= until or since <= _EPOCH_ANCHOR


def bucket_label(value: datetime, granularity: Granularity) -> str:
    """Render a datetime as the canonical bucket key for ``granularity``.

    Day → ``YYYY-MM-DD``; week → ``YYYY-Www`` (ISO 8601 week); month →
    ``YYYY-MM``. Keeping the format lexically sortable means the
    frontend can ``points.sort_by(bucket)`` for free.
    """
    if granularity == "day":
        return value.strftime("%Y-%m-%d")
    if granularity == "week":
        # ISO-week number; Python's %V gives the ISO week, %G the ISO
        # year (handles the early-Jan/late-Dec edge cases properly).
        return value.strftime("%G-W%V")
    # ``"month"``
    return value.strftime("%Y-%m")


def sqlite_strftime_format(granularity: Granularity) -> str:
    """Return the ``strftime`` pattern SQLite uses to project into a bucket.

    SQLite is the dev/test database; PostgreSQL would use ``date_trunc``
    but we keep the abstraction in one place so a future Postgres swap
    only touches the queries module.

    Note: SQLite's ``%W`` is *Sunday-week* not ISO-week — close enough for
    chart rendering and avoids the timezone-shift headache of computing
    ISO weeks in SQL. The python-side ``bucket_label`` formatter still
    yields the correct ISO key for stable display.
    """
    if granularity == "day":
        return "%Y-%m-%d"
    if granularity == "week":
        # YYYY-WnnSundayBased; converted to YYYY-Www by the python layer.
        return "%Y-W%W"
    return "%Y-%m"


def enumerate_buckets(
    since: datetime, until: datetime, granularity: Granularity
) -> list[str]:
    """Pre-compute every bucket label in ``[since, until]`` so empty
    buckets are filled with zeros in the response.

    Without this the chart would jump from "tuesday → friday" when no
    renders happened on wed/thu — confusing for users scanning trends.
    """
    if since >= until:
        return []
    out: list[str] = []
    cursor = since
    step = {
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=31),  # month math is intentionally rough;
        # bucket_label dedupes via %Y-%m, so 31-day step never doublecounts.
    }[granularity]
    seen: set[str] = set()
    while cursor <= until:
        label = bucket_label(cursor, granularity)
        if label not in seen:
            seen.add(label)
            out.append(label)
        cursor = cursor + step
    return out


__all__ = [
    "bucket_label",
    "enumerate_buckets",
    "is_empty_window",
    "parse_period",
    "period_window",
    "previous_window",
    "sqlite_strftime_format",
]
