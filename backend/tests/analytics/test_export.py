"""End-to-end tests for ``GET /analytics/export``."""

from __future__ import annotations

import csv
import io
import json


def test_export_videos_csv(isolated_db, workspace_headers, seeded_analytics):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=videos&format=csv",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "analytics-videos-30d.csv" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 12  # one row per project
    assert "project_id" in rows[0]
    assert "render_count" in rows[0]


def test_export_videos_json(isolated_db, workspace_headers, seeded_analytics):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=videos&format=json",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    body = json.loads(r.text)
    assert body["kind"] == "videos"
    assert body["period"] == "30d"
    assert body["workspace_id"] == 1
    assert len(body["rows"]) == 12


def test_export_trends_csv_with_granularity(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=trends&format=csv&period=7d&granularity=week",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    text = r.text
    assert "bucket" in text


def test_export_overview_csv_emits_kpi_rows(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=overview&format=csv",
        headers=workspace_headers,
    )
    rows = list(csv.DictReader(io.StringIO(r.text)))
    keys = {r["key"] for r in rows}
    assert "videos_total" in keys
    assert "renders_total" in keys


def test_export_templates_csv(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=templates&format=csv",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    rows = list(csv.DictReader(io.StringIO(r.text)))
    slugs = {r["slug"] for r in rows}
    assert slugs <= {"vlog_warm", "tutorial_steady",
                     "product_demo_vertical", "social_punchy"}


def test_export_empty_db_returns_empty_csv(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=videos&format=csv",
        headers=workspace_headers,
    )
    assert r.status_code == 200
    assert r.text == ""


def test_export_rejects_unknown_kind(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=mystery&format=csv",
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_export_rejects_unknown_format(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=videos&format=xlsx",
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_export_sets_attachment_header(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/export?kind=videos&format=json&period=7d",
        headers=workspace_headers,
    )
    cd = r.headers["content-disposition"]
    assert "attachment" in cd
    assert "analytics-videos-7d.json" in cd
