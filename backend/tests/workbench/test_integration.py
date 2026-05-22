"""Integration tests that prove the Workbench really is plugged into the
real mix-video / brand-kit / templates surfaces (not a parallel fixture).

These don't *run* ffmpeg — that would make tests slow and ffmpeg-bound. They
just walk the full HTTP path so a refactor of mix-video or brand-kit that
breaks the Workbench's contracts fails here, loudly, instead of silently in
production.
"""

from __future__ import annotations


def test_workbench_picks_up_mix_video_task_after_submission(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """Inject a task into mix-video's registry the same way submit_mix would.

    Calling ``POST /api/v1/mix-video`` for real would kick off an ffmpeg job
    via BackgroundTasks. We skip the ffmpeg detour by writing directly into
    the same in-memory dict that endpoint maintains — proving the Workbench
    is wired to the same store.
    """
    mix_video_tasks_reset["wb-test-1"] = {
        "task_id": "wb-test-1",
        "status": "running",
        "progress": 0.1,
        "project_id": 9999,  # no DB row; live-only task
        "preset": "social_9x16",
    }

    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    # 9999 has no project row in *any* workspace, so it stays in the global
    # pool (project_ids filter only kicks in when the workspace has projects).
    # The point of this test: the endpoint reads the same dict.
    assert any(t["task_id"] == "wb-test-1" for t in body["items"])


def test_workbench_overview_brand_kit_matches_brand_kit_endpoint(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """Workbench shows the same kit the mix-video pipeline will apply."""
    # Materialise the default workspace kit and tweak the accent so we can
    # detect drift in either direction.
    isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"accent_color": "#FF1F44", "primary_color": "#012345"},
    )

    workbench = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    kit = isolated_db.get("/api/v1/brand-kit", headers=workspace_headers).json()

    assert workbench["brand_kit"] is not None
    assert workbench["brand_kit"]["accent_color"] == kit["accent_color"]
    assert workbench["brand_kit"]["primary_color"] == kit["primary_color"]
    assert workbench["brand_kit"]["id"] == kit["id"]


def test_workbench_featured_templates_match_templates_endpoint(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """Names returned by /workbench/overview must be a subset of /templates."""
    overview = isolated_db.get(
        "/api/v1/workbench/overview", headers=workspace_headers
    ).json()
    templates = isolated_db.get(
        "/api/v1/templates", headers=workspace_headers
    ).json()

    overview_names = {t["name"] for t in overview["featured_templates"]}
    all_names = {t["name"] for t in templates["items"]}
    assert overview_names <= all_names


def test_workbench_user_scoped_brand_kit_wins_over_workspace_default(
    isolated_db, user_headers, workspace_headers, mix_video_tasks_reset
):
    """User-scoped kit must shadow the workspace kit in the overview."""
    # Workspace default.
    isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    # Create + activate a user-scoped override.
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=user_headers,
        json={
            "scope": "user",
            "owner_id": 42,
            "is_active": True,
            "name": "Ava 的个人套件",
            "accent_color": "#7C3AED",
        },
    )
    assert r.status_code == 201, r.text

    body = isolated_db.get(
        "/api/v1/workbench/overview", headers=user_headers
    ).json()
    assert body["brand_kit"] is not None
    assert body["brand_kit"]["scope"] == "user"
    assert body["brand_kit"]["accent_color"] == "#7C3AED"
