"""End-to-end tests for ``GET /analytics/brand-kits``."""

from __future__ import annotations


def test_brand_kits_empty_db(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/analytics/brand-kits", headers=workspace_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_brand_kits_lists_all_workspace_kits(
    isolated_db, workspace_headers, seeded_analytics
):
    r = isolated_db.get(
        "/api/v1/analytics/brand-kits?period=30d", headers=workspace_headers
    )
    body = r.json()
    # Workspace 1 has bk1 (active workspace), bk2 (inactive workspace), bk3 (user).
    names = {it["name"] for it in body["items"]}
    assert names == {"Acme Default", "Acme Legacy", "Bo's Personal Kit"}


def test_brand_kits_excludes_other_workspaces(
    isolated_db, workspace_headers, seeded_analytics
):
    """The workspace-2 kit must not appear in workspace-1's response."""
    r = isolated_db.get(
        "/api/v1/analytics/brand-kits", headers=workspace_headers
    )
    body = r.json()
    names = {it["name"] for it in body["items"]}
    assert "Other Tenant Kit" not in names


def test_brand_kits_usage_counts_match_seed(
    isolated_db, workspace_headers, seeded_analytics
):
    """The ``projects`` counter should reflect how many seed projects
    chose each kit via ``Project.config['brand_kit_id']``."""
    r = isolated_db.get(
        "/api/v1/analytics/brand-kits", headers=workspace_headers
    )
    body = r.json()
    by_name = {it["name"]: it for it in body["items"]}
    # bk1 (Acme Default) — referenced by 8 of the 12 seed projects.
    assert by_name["Acme Default"]["projects"] == 8
    # bk3 (Bo's Personal Kit) — referenced by 3 projects.
    assert by_name["Bo's Personal Kit"]["projects"] == 3
    # bk2 — never referenced by any project.
    assert by_name["Acme Legacy"]["projects"] == 0
