"""End-to-end tests for ``GET /analytics/team``."""

from __future__ import annotations


def test_team_empty_db(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/analytics/team", headers=workspace_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_team_lists_active_members_with_counts(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/team?period=30d", headers=workspace_headers
    )
    body = r.json()
    # The seed gives u1 + u2 + u3 each at least one project in the 30d
    # window — all three should appear.
    by_email = {it["email"]: it for it in body["items"]}
    assert "ada@acme.com" in by_email
    assert "bo@acme.com" in by_email
    # Counts are non-negative and sum to the seed.
    assert sum(it["projects"] for it in body["items"]) == 12


def test_team_limit_caps_rows(isolated_db, workspace_headers, seeded_analytics):
    r = isolated_db.get(
        "/api/v1/analytics/team?limit=1", headers=workspace_headers
    )
    body = r.json()
    assert len(body["items"]) == 1


def test_team_rejects_bad_limit(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/analytics/team?limit=0", headers=workspace_headers
    )
    assert r.status_code == 422
