"""End-to-end tests for ``GET /analytics/templates``."""

from __future__ import annotations


def test_templates_empty_db_returns_no_items(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/templates", headers=workspace_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total_uses"] == 0


def test_templates_ranking_reflects_seed(
    isolated_db, workspace_headers, seeded_analytics
):
    """Templates ranked by uses, with name/category enriched from Template table."""
    r = isolated_db.get(
        "/api/v1/analytics/templates?period=30d", headers=workspace_headers
    )
    body = r.json()
    assert body["total_uses"] >= 12  # 12 projects each pick a template

    by_slug = {it["slug"]: it for it in body["items"]}
    # Top of ranking should be vlog_warm (4 projects use it in the seed).
    assert body["items"][0]["slug"] == "vlog_warm"
    assert by_slug["vlog_warm"]["uses"] == 4
    assert by_slug["vlog_warm"]["name"] == "Warm Vlog"
    assert by_slug["vlog_warm"]["category"] == "marketing"


def test_templates_pct_sums_to_one(
    isolated_db, workspace_headers, seeded_analytics
):
    """The pct field should be each row's uses / total_uses."""
    r = isolated_db.get(
        "/api/v1/analytics/templates?period=30d", headers=workspace_headers
    )
    body = r.json()
    total_pct = sum(it["pct"] for it in body["items"])
    # Floating-point tolerance: 4 templates * round(pct, 4) ≤ 1.0.
    assert 0.999 <= total_pct <= 1.001


def test_templates_limit_caps_items(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/templates?limit=2", headers=workspace_headers
    )
    body = r.json()
    assert len(body["items"]) == 2


def test_templates_limit_validation(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/templates?limit=0", headers=workspace_headers
    )
    assert r.status_code == 422


def test_templates_isolation(
    isolated_db, other_workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/templates", headers=other_workspace_headers
    )
    body = r.json()
    # Workspace 2 has 3 projects all using vlog_warm.
    assert len(body["items"]) == 1
    assert body["items"][0]["slug"] == "vlog_warm"
    assert body["items"][0]["uses"] == 3
