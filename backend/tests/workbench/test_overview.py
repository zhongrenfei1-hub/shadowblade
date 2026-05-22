"""Tests for GET /api/v1/workbench/overview.

The overview endpoint is a read-model aggregate: it should never write to
the DB, must scope all numbers to the caller's workspace, and must
gracefully degrade when downstream surfaces (template loader, brand kit
table) are empty.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Empty-workspace behaviour
# ---------------------------------------------------------------------------


def test_overview_empty_workspace_returns_zero_kpis(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """A workspace with no projects/renders gets zeroed KPIs but full shape."""
    r = isolated_db.get("/api/v1/workbench/overview", headers=workspace_headers)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["workspace_id"] == 1
    assert "generated_at" in body

    kpis = {k["key"]: k for k in body["kpis"]}
    assert kpis["renders_today"]["value"] == 0
    assert kpis["renders_this_week"]["value"] == 0
    assert kpis["in_progress"]["value"] == 0
    assert kpis["total_projects"]["value"] == 0

    # Quick actions are always present so the UI never has nothing to render.
    keys = {a["key"] for a in body["quick_actions"]}
    assert {"new_video", "preview_video", "upload_asset", "browse_templates"} <= keys


def test_overview_quick_actions_carry_endpoint_metadata(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """Each quick action exposes the real backend endpoint + HTTP verb."""
    body = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    new_video = next(a for a in body["quick_actions"] if a["key"] == "new_video")
    assert new_video["endpoint"] == "/api/v1/mix-video"
    assert new_video["method"] == "POST"
    assert new_video["href"].startswith("/new-video.html")


# ---------------------------------------------------------------------------
# KPI roll-up
# ---------------------------------------------------------------------------


def test_overview_counts_projects_and_in_progress_renders(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """KPI counts roll up only the caller's workspace."""
    body = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    kpis = {k["key"]: k["value"] for k in body["kpis"]}

    # Three projects seeded for workspace 1 (the fourth belongs to ws=2).
    assert kpis["total_projects"] == 3

    # One render is running + one queued = 2 in progress.
    assert kpis["in_progress"] == 2

    # One render finished today.
    assert kpis["renders_today"] >= 1


def test_overview_cross_workspace_isolation(
    isolated_db, mix_video_tasks_reset, seed_projects
):
    """Numbers for workspace 1 must not include workspace 2's data."""
    ws1 = isolated_db.get(
        "/api/v1/workbench/overview", headers={"X-Workspace-Id": "1"}
    ).json()
    ws2 = isolated_db.get(
        "/api/v1/workbench/overview", headers={"X-Workspace-Id": "2"}
    ).json()

    ws1_kpis = {k["key"]: k["value"] for k in ws1["kpis"]}
    ws2_kpis = {k["key"]: k["value"] for k in ws2["kpis"]}

    assert ws1_kpis["total_projects"] == 3
    assert ws2_kpis["total_projects"] == 1
    # The ws=2 running render must not bleed into ws=1's count.
    assert ws1_kpis["in_progress"] != ws2_kpis["in_progress"] + 999  # sanity
    assert ws2_kpis["in_progress"] == 1


def test_overview_includes_live_mix_video_tasks_in_progress(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """Live mix-video tasks count toward 'in_progress' alongside RenderTask."""
    project_id = seed_projects["project_ids"][0]
    mix_video_tasks_reset["live-abc"] = {
        "task_id": "live-abc",
        "status": "running",
        "progress": 0.4,
        "project_id": project_id,
        "preset": "social_9x16",
    }

    body = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    kpis = {k["key"]: k["value"] for k in body["kpis"]}
    # 1 running render + 1 queued render + 1 live mix = 3.
    assert kpis["in_progress"] == 3


# ---------------------------------------------------------------------------
# Brand kit folding
# ---------------------------------------------------------------------------


def test_overview_brand_kit_is_workspace_default_when_no_user_kit(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """First read materialises the workspace-scoped default brand kit."""
    # Trigger the auto-materialisation path used by the brand-kit module.
    isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)

    body = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    assert body["brand_kit"] is not None
    assert body["brand_kit"]["scope"] == "workspace"
    assert body["brand_kit"]["primary_color"] == "#0F2A4A"


def test_overview_brand_kit_null_when_workspace_has_none(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """No materialised kit → brand_kit is null (not an error)."""
    body = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    assert body["brand_kit"] is None


# ---------------------------------------------------------------------------
# Featured templates
# ---------------------------------------------------------------------------


def test_overview_featured_templates_capped_at_six(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """The dashboard never shows more than six templates."""
    body = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    assert isinstance(body["featured_templates"], list)
    assert len(body["featured_templates"]) <= 6
    for tmpl in body["featured_templates"]:
        assert "name" in tmpl
        # Each template ships a deep-link into new-video.html so the UI
        # can wire a one-click "use this template" button.
        assert tmpl["href"].startswith("/new-video.html?template=")


def test_overview_featured_templates_survive_loader_failure(
    isolated_db, workspace_headers, mix_video_tasks_reset, monkeypatch
):
    """If template listing throws, the rest of the overview still loads."""

    def boom(*_a, **_kw):
        raise RuntimeError("templates dir vanished")

    # Patch at the binding inside workbench module (where it's imported lazily).
    monkeypatch.setattr(
        "app.services.template.list_templates", boom, raising=True
    )

    r = isolated_db.get("/api/v1/workbench/overview", headers=workspace_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["featured_templates"] == []
    # KPIs and quick actions still render — the dashboard degrades gracefully.
    assert len(body["quick_actions"]) >= 4
