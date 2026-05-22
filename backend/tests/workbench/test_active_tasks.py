"""Tests for GET /api/v1/workbench/active-tasks.

This endpoint unions two task sources — the RenderTask ORM table (persisted
work) and the in-memory ``_TASKS`` dict from :mod:`app.api.mix_video` (live
work) — so the dashboard always shows a single coherent timeline.
"""

from __future__ import annotations


def test_active_tasks_empty(
    isolated_db, workspace_headers, mix_video_tasks_reset
):
    """No work anywhere → empty union, but full envelope is intact."""
    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["sources"] == {"render_queue": 0, "mix_video": 0}
    assert body["workspace_id"] == 1


def test_active_tasks_returns_only_running_and_queued_from_db(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """Succeeded RenderTask rows are filtered out of the active timeline."""
    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    db_items = [t for t in body["items"] if t["source"] == "render_queue"]

    assert len(db_items) == 2  # one running, one queued
    statuses = {t["status"] for t in db_items}
    assert statuses == {"running", "queued"}
    # Succeeded row from seed is filtered.
    assert all(t["status"] != "succeeded" for t in db_items)


def test_active_tasks_resolves_project_name(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """RenderTask items carry the human-readable project name, not just id."""
    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    running = next(
        t for t in body["items"]
        if t["source"] == "render_queue" and t["status"] == "running"
    )
    assert running["project_name"] == "春季产品发布"
    assert running["progress"] == 0.62
    assert running["priority"] == "rush"
    assert running["worker"] == "gpu-cluster-3"


def test_active_tasks_merges_live_mix_video(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """In-memory mix-video tasks are unioned with RenderTask rows."""
    pid = seed_projects["project_ids"][0]
    mix_video_tasks_reset["live-xyz"] = {
        "task_id": "live-xyz",
        "status": "running",
        "progress": 0.91,
        "project_id": pid,
        "preset": "social_9x16",
        "output_path": None,
    }

    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    sources = {t["source"] for t in body["items"]}
    assert "render_queue" in sources
    assert "mix_video" in sources

    live = next(t for t in body["items"] if t["task_id"] == "live-xyz")
    assert live["source"] == "mix_video"
    assert live["progress"] == 0.91


def test_active_tasks_skips_other_workspace_live_tasks(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """Live mix tasks whose project belongs to ws=2 must not leak to ws=1."""
    ws2_pid = seed_projects["ws2_project_id"]
    mix_video_tasks_reset["live-other-ws"] = {
        "task_id": "live-other-ws",
        "status": "running",
        "progress": 0.5,
        "project_id": ws2_pid,
        "preset": "social_9x16",
    }

    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    task_ids = {t["task_id"] for t in body["items"]}
    assert "live-other-ws" not in task_ids


def test_active_tasks_sort_running_before_queued(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """Sort priority is running > queued so the eye lands on live work first."""
    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    statuses = [t["status"] for t in body["items"]]
    # Find first 'queued' — every status before it must be 'running'.
    if "queued" in statuses:
        first_queued = statuses.index("queued")
        assert all(s == "running" for s in statuses[:first_queued])


def test_active_tasks_handles_string_project_id(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """Mix-video allows ``project_id`` as a string — match must still work."""
    pid = seed_projects["project_ids"][0]
    mix_video_tasks_reset["live-strpid"] = {
        "task_id": "live-strpid",
        "status": "running",
        "progress": 0.2,
        "project_id": str(pid),  # string, not int
        "preset": "social_9x16",
    }

    body = isolated_db.get(
        "/api/v1/workbench/active-tasks", headers=workspace_headers
    ).json()
    ids = {t["task_id"] for t in body["items"]}
    assert "live-strpid" in ids


def test_active_tasks_include_recent_succeeded_toggle(
    isolated_db, workspace_headers, mix_video_tasks_reset, seed_projects
):
    """``include_recent_succeeded=false`` strips finished mix-video tasks."""
    pid = seed_projects["project_ids"][0]
    mix_video_tasks_reset["live-done"] = {
        "task_id": "live-done",
        "status": "succeeded",
        "progress": 1.0,
        "project_id": pid,
        "output_path": "/tmp/done.mp4",
    }

    keep = isolated_db.get(
        "/api/v1/workbench/active-tasks?include_recent_succeeded=true",
        headers=workspace_headers,
    ).json()
    drop = isolated_db.get(
        "/api/v1/workbench/active-tasks?include_recent_succeeded=false",
        headers=workspace_headers,
    ).json()

    keep_ids = {t["task_id"] for t in keep["items"]}
    drop_ids = {t["task_id"] for t in drop["items"]}
    assert "live-done" in keep_ids
    assert "live-done" not in drop_ids
