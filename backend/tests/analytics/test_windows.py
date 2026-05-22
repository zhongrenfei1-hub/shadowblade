"""Unit tests for :mod:`app.services.analytics.windows` — pure-Python,
no DB, no client. These pin the period/bucket math because every other
test depends on it being correct.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.services.analytics.windows import (
    bucket_label,
    enumerate_buckets,
    is_empty_window,
    parse_period,
    period_window,
    previous_window,
)


def test_parse_period_accepts_known_values():
    for p in ("7d", "30d", "90d", "all"):
        assert parse_period(p) == p


def test_parse_period_rejects_unknown():
    with pytest.raises(ValueError, match="unknown period"):
        parse_period("1y")


def test_period_window_7d():
    now = datetime(2026, 5, 22, 12, 0, 0)
    since, until = period_window("7d", now=now)
    assert until == now
    assert (until - since) == timedelta(days=7)


def test_period_window_30d():
    now = datetime(2026, 5, 22)
    since, until = period_window("30d", now=now)
    assert (until - since) == timedelta(days=30)


def test_period_window_all_returns_far_anchor():
    now = datetime(2026, 5, 22)
    since, until = period_window("all", now=now)
    assert since.year <= 2001  # anchored at 2000-01-01 sentinel
    assert until == now


def test_previous_window_is_immediately_before():
    since = datetime(2026, 5, 1)
    until = datetime(2026, 5, 22)
    p_since, p_until = previous_window(since, until)
    assert p_until == since
    assert (p_until - p_since) == (until - since)


def test_previous_window_degenerate_for_all_period():
    since = datetime(2000, 1, 1)
    until = datetime(2026, 5, 22)
    p_since, _ = previous_window(since, until)
    # The "all" period collapses the prior window into the pre-2000 era,
    # which is_empty_window correctly classifies as undefined.
    assert is_empty_window(p_since, since) is True


def test_bucket_label_day():
    dt = datetime(2026, 5, 22, 11, 30)
    assert bucket_label(dt, "day") == "2026-05-22"


def test_bucket_label_week():
    # 2026-05-22 is a Friday — ISO week 21 of 2026
    dt = datetime(2026, 5, 22)
    assert bucket_label(dt, "week") == "2026-W21"


def test_bucket_label_month():
    dt = datetime(2026, 5, 22)
    assert bucket_label(dt, "month") == "2026-05"


def test_enumerate_buckets_day_fills_range():
    since = datetime(2026, 5, 20)
    until = datetime(2026, 5, 22, 23, 59)
    buckets = enumerate_buckets(since, until, "day")
    # Should contain 5-20, 5-21, 5-22 (3 days).
    assert buckets[0] == "2026-05-20"
    assert "2026-05-21" in buckets
    assert buckets[-1] == "2026-05-22"
    assert len(buckets) == 3


def test_enumerate_buckets_month_dedupes():
    since = datetime(2026, 1, 1)
    until = datetime(2026, 3, 30)
    buckets = enumerate_buckets(since, until, "month")
    assert buckets == ["2026-01", "2026-02", "2026-03"]


def test_enumerate_buckets_empty_window():
    since = datetime(2026, 5, 22)
    until = since
    assert enumerate_buckets(since, until, "day") == []
