"""End-to-end cache-behaviour tests at the API boundary."""

from __future__ import annotations


def test_endpoint_marks_cached_on_second_call(
    isolated_db, workspace_headers, seeded_analytics
):
    """First call sets the cache; second call comes back with ``cached: true``."""
    first = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=workspace_headers
    ).json()
    assert first["cached"] is False
    second = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=workspace_headers
    ).json()
    assert second["cached"] is True
    # The body is otherwise identical aside from the flag and generated_at.
    assert second["totals"] == first["totals"]


def test_different_periods_have_separate_cache_entries(
    isolated_db, workspace_headers, seeded_analytics
):
    isolated_db.get(
        "/api/v1/analytics/overview?period=7d", headers=workspace_headers
    )
    # 30d is a fresh key — should report cached=False
    r = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=workspace_headers
    )
    assert r.json()["cached"] is False


def test_different_workspaces_have_separate_cache_entries(
    isolated_db, workspace_headers, other_workspace_headers, seeded_analytics
):
    isolated_db.get("/api/v1/analytics/overview", headers=workspace_headers)
    r = isolated_db.get(
        "/api/v1/analytics/overview", headers=other_workspace_headers
    )
    assert r.json()["cached"] is False
    assert r.json()["workspace_id"] == 2


def test_cache_persists_across_endpoints_independently(
    isolated_db, workspace_headers, seeded_analytics
):
    """Cache keys are scoped per endpoint; calling /trends doesn't warm /overview."""
    isolated_db.get(
        "/api/v1/analytics/trends?period=30d&granularity=day",
        headers=workspace_headers,
    )
    overview = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=workspace_headers
    ).json()
    assert overview["cached"] is False
