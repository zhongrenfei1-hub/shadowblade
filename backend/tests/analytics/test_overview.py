"""End-to-end tests for ``GET /analytics/overview``."""

from __future__ import annotations


def test_overview_legacy_flag_returns_fixture(isolated_db, workspace_headers):
    """``legacy=true`` continues to serve the demo fixture shape."""
    r = isolated_db.get(
        "/api/v1/analytics/overview?legacy=true", headers=workspace_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Fixture shape has these three top-level keys.
    assert {"kpis", "timeseries", "distribution"} <= set(body.keys())
    assert isinstance(body["kpis"], list) and len(body["kpis"]) >= 1


def test_overview_empty_workspace_returns_zero_kpis(isolated_db, workspace_headers):
    """No projects → all KPI values are 0, deltas are None."""
    r = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=workspace_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workspace_id"] == 1
    assert body["period"] == "30d"
    assert body["cached"] is False
    by_key = {k["key"]: k for k in body["kpis"]}
    assert by_key["videos_total"]["value"] == 0.0
    assert by_key["renders_total"]["value"] == 0.0
    # success rate is 0.0 not "—" when there are zero renders
    assert by_key["success_rate"]["value"] == 0.0
    # storage delta is intentionally None
    assert by_key["storage_bytes"]["delta"] is None


def test_overview_returns_real_counts_when_seeded(
    isolated_db, workspace_headers, seeded_analytics
):
    """With seeded data, KPIs reflect the actual project / render counts."""
    r = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=workspace_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    totals = body["totals"]
    # 12 projects seeded for workspace 1
    assert totals["projects_total"] == 12
    # 18 render tasks for workspace 1 (excludes the 3 workspace-2 renders)
    assert totals["renders_total"] == seeded_analytics["ws1_renders_total"]
    assert totals["renders_succeeded"] == seeded_analytics["ws1_succeeded"]
    assert totals["renders_failed"] == seeded_analytics["ws1_failed"]
    # storage_bytes is workspace-wide, not windowed
    assert totals["storage_bytes"] == seeded_analytics["ws1_storage_bytes"]


def test_overview_kpis_have_expected_keys(
    isolated_db, workspace_headers, seeded_analytics
):
    """Frontend joins on KPI keys — they must be stable."""
    r = isolated_db.get(
        "/api/v1/analytics/overview", headers=workspace_headers
    )
    body = r.json()
    keys = {k["key"] for k in body["kpis"]}
    assert keys == {
        "videos_total",
        "renders_total",
        "success_rate",
        "avg_runtime_seconds",
        "total_runtime_seconds",
        "storage_bytes",
    }


def test_overview_success_rate_is_ratio_between_zero_and_one(
    isolated_db, workspace_headers, seeded_analytics
):
    """``success_rate`` is a unit-less ratio — never > 1, never < 0."""
    r = isolated_db.get("/api/v1/analytics/overview", headers=workspace_headers)
    body = r.json()
    sr = next(k for k in body["kpis"] if k["key"] == "success_rate")
    assert 0.0 <= sr["value"] <= 1.0
    assert sr["unit"] == "ratio"


def test_overview_distribution_groups_by_purpose(
    isolated_db, workspace_headers, seeded_analytics
):
    """The purpose donut chart matches the project distribution."""
    r = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=workspace_headers
    )
    body = r.json()
    labels = {b["label"] for b in body["distribution"]}
    # All four purposes appear (seed plants at least one of each).
    assert labels == {"marketing", "training", "product_demo", "social"}
    # Sum of all distributions equals total projects.
    total = sum(b["value"] for b in body["distribution"])
    assert total == body["totals"]["projects_total"]


def test_overview_isolates_other_workspace(
    isolated_db, other_workspace_headers, seeded_analytics
):
    """Workspace 2 sees its own 3 projects, not workspace 1's 12."""
    r = isolated_db.get(
        "/api/v1/analytics/overview?period=30d", headers=other_workspace_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workspace_id"] == 2
    assert body["totals"]["projects_total"] == 3


def test_overview_rejects_unknown_period(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/overview?period=bogus", headers=workspace_headers
    )
    assert r.status_code == 422
    assert "unknown period" in r.json()["detail"]


def test_overview_default_period_is_30d(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/analytics/overview", headers=workspace_headers)
    assert r.status_code == 200
    assert r.json()["period"] == "30d"


def test_overview_period_all_includes_everything(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/overview?period=all", headers=workspace_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["period"] == "all"
    # ``all`` should NEVER set deltas because the prior window is undefined.
    for k in body["kpis"]:
        assert k["delta"] is None
