"""End-to-end tests for ``GET /analytics/trends``."""

from __future__ import annotations

from datetime import datetime, timedelta


def test_trends_default_granularity_is_day(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/analytics/trends", headers=workspace_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["granularity"] == "day"


def test_trends_empty_db_returns_zero_buckets(isolated_db, workspace_headers):
    """Empty DB still produces a continuous range of zero-filled buckets."""
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=7d&granularity=day",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    body = r.json()
    points = body["points"]
    # 7-day window → 8 calendar-day buckets (today partial + 7 prior days,
    # depending on hour of run). Allow [7, 9] to accommodate boundary
    # jitter when the run straddles midnight.
    assert 7 <= len(points) <= 9
    # Every bucket has zero counters when the DB is empty.
    for p in points:
        assert p["rendered"] == 0
        assert p["succeeded"] == 0
        assert p["failed"] == 0


def test_trends_day_buckets_reflect_seed(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=7d&granularity=day",
        headers=workspace_headers,
    )
    body = r.json()
    points = body["points"]
    total_rendered = sum(p["rendered"] for p in points)
    total_succeeded = sum(p["succeeded"] for p in points)
    total_failed = sum(p["failed"] for p in points)
    # Render-task counts from the seed should be present in the bucketed view.
    assert total_rendered == seeded_analytics["ws1_renders_total"]
    assert total_succeeded == seeded_analytics["ws1_succeeded"]
    assert total_failed == seeded_analytics["ws1_failed"]


def test_trends_buckets_are_sortable_strings(
    isolated_db, workspace_headers, seeded_analytics
):
    """Bucket labels are formatted so a lexical sort is also a temporal sort."""
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=7d&granularity=day",
        headers=workspace_headers,
    )
    points = r.json()["points"]
    labels = [p["bucket"] for p in points]
    assert labels == sorted(labels)


def test_trends_week_granularity(isolated_db, workspace_headers, seeded_analytics):
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=30d&granularity=week",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["granularity"] == "week"
    # ISO week format check: YYYY-Www
    for p in body["points"]:
        bucket = p["bucket"]
        assert "-W" in bucket, bucket
        year_part, week_part = bucket.split("-W")
        assert len(year_part) == 4 and year_part.isdigit()
        assert len(week_part) == 2 and week_part.isdigit()


def test_trends_month_granularity(isolated_db, workspace_headers, seeded_analytics):
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=90d&granularity=month",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["granularity"] == "month"
    for p in body["points"]:
        assert len(p["bucket"]) == 7  # YYYY-MM


def test_trends_rejects_unknown_granularity(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/trends?granularity=hour", headers=workspace_headers
    )
    assert r.status_code == 422
    assert "unknown granularity" in r.json()["detail"]


def test_trends_rejects_unknown_period(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=foobar", headers=workspace_headers
    )
    assert r.status_code == 422


def test_trends_isolates_other_workspace(
    isolated_db, other_workspace_headers, seeded_analytics
):
    """Workspace 2 trends do not include workspace 1's renders."""
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=7d&granularity=day",
        headers=other_workspace_headers,
    )
    body = r.json()
    assert body["workspace_id"] == 2
    total = sum(p["rendered"] for p in body["points"])
    # workspace 2 has exactly 3 succeeded renders seeded.
    assert total == 3


def test_trends_avg_runtime_uses_only_succeeded(
    isolated_db, workspace_headers, seeded_analytics
):
    """Failed renders must NOT pull down the avg_runtime average."""
    r = isolated_db.get(
        "/api/v1/analytics/trends?period=7d&granularity=day",
        headers=workspace_headers,
    )
    points = r.json()["points"]
    # Find a bucket with both succeeded and failed renders (Project 1's day).
    for p in points:
        if p["succeeded"] >= 1 and p["failed"] >= 1:
            # The failed run had estimated_seconds=3.5; if it were counted
            # the avg would drop near 13. We expect the avg to reflect the
            # succeeded runtimes only (18.0 and 22.0 for project 1).
            assert p["avg_runtime_seconds"] >= 15.0, (
                f"avg_runtime_seconds {p['avg_runtime_seconds']} suggests failed "
                f"renders are leaking into the average"
            )
            break
