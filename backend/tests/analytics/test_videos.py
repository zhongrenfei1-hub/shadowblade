"""End-to-end tests for ``GET /analytics/videos``."""

from __future__ import annotations


def test_videos_default_pagination(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get("/api/v1/analytics/videos", headers=workspace_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 12
    assert len(body["items"]) == 12  # 12 fits in one page


def test_videos_pagination_clamps_page_size_high(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/videos?page_size=300", headers=workspace_headers
    )
    assert r.status_code == 422  # caught at FastAPI validation layer


def test_videos_pagination_returns_correct_slice(
    isolated_db, workspace_headers, seeded_analytics
):
    r1 = isolated_db.get(
        "/api/v1/analytics/videos?page=1&page_size=5", headers=workspace_headers
    )
    r2 = isolated_db.get(
        "/api/v1/analytics/videos?page=2&page_size=5", headers=workspace_headers
    )
    p1, p2 = r1.json(), r2.json()
    assert p1["total"] == p2["total"] == 12
    assert len(p1["items"]) == 5
    assert len(p2["items"]) == 5
    # No overlap between pages.
    ids1 = {it["project_id"] for it in p1["items"]}
    ids2 = {it["project_id"] for it in p2["items"]}
    assert ids1.isdisjoint(ids2)


def test_videos_filter_by_status(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/videos?status=done", headers=workspace_headers
    )
    body = r.json()
    # Seed: 6 projects have status='done' (indices 0, 1, 4, 5, 8, 11).
    assert all(it["status"] == "done" for it in body["items"])
    assert body["total"] == 6


def test_videos_filter_by_purpose(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/videos?purpose=training", headers=workspace_headers
    )
    body = r.json()
    assert all(it["purpose"] == "training" for it in body["items"])
    assert body["total"] >= 1


def test_videos_render_aggregates_correct(
    isolated_db, workspace_headers, seeded_analytics
):
    """Per-project ``render_count``, ``success_rate`` reflect the seed."""
    r = isolated_db.get(
        "/api/v1/analytics/videos?page_size=200", headers=workspace_headers
    )
    body = r.json()
    by_name = {it["name"]: it for it in body["items"]}
    # Project 1 had 3 renders: 2 succeeded + 1 failed → success_rate ≈ 2/3.
    p1 = by_name["Project 1"]
    assert p1["render_count"] == 3
    assert p1["success_count"] == 2
    assert p1["failed_count"] == 1
    assert 0.65 <= p1["success_rate"] <= 0.67


def test_videos_isolation(
    isolated_db, other_workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/videos", headers=other_workspace_headers
    )
    body = r.json()
    assert body["workspace_id"] == 2
    assert body["total"] == 3
    names = [it["name"] for it in body["items"]]
    assert all("Other Project" in n for n in names)
