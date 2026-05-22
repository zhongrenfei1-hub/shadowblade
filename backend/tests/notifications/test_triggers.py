"""Integration tests for the trigger hooks.

Covers the points where ShadowBlade's existing features push events
into the inbox:

* ``api.mix_video._run_async_mix`` → notify_video_generated / failed
* ``api.brand_kits.update_active_brand_kit`` → notify_brand_kit_changed
* ``api.brand_kits.upload_brand_kit_logo`` → notify_brand_kit_changed

These tests run with a *mocked* mix pipeline because the real one would
need ffmpeg and a real render — too slow for CI. The brand-kit hooks
exercise the live API end-to-end (no mocking) since they only touch the
SQLAlchemy session.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.api import mix_video as mv
from app.services import notifications as svc

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# mix-video success path
# ---------------------------------------------------------------------------


class _FakePipelineResult:
    def __init__(self) -> None:
        self.project_id = 7
        self.output_path = "/tmp/fake.mp4"
        self.cover_path = "/tmp/fake.jpg"
        self.duration = 12.5
        self.preset = "social_9x16"
        self.used_hardware = False
        self.transitions = ["editorial"]
        self.runtime_seconds = 3.2
        self.warnings: list[str] = []
        self.subtitle_report = None
        self.beat_grid = None


class _FakePipeline:
    async def run(self, _req):
        return _FakePipelineResult()


async def test_mix_video_success_creates_notification(
    monkeypatch,
    test_workspace_id: int,
    test_user_id: int,
):
    """A render task that succeeds should land a video_generated notification."""

    # Patch the pipeline so we don't need ffmpeg.
    monkeypatch.setattr(mv, "MixPipeline", lambda: _FakePipeline())

    # Build a minimal request — _build_mix_request only needs clips and
    # project_id; the fake pipeline ignores the request anyway.
    from app.api.mix_video import MixVideoRequest

    body = MixVideoRequest(
        project_id=7,
        clips=[{"path": "/tmp/x.mp4"}],
    )
    # _run_async_mix expects the slot to already exist (created by the
    # submit handler before the background task fires).
    mv._TASKS["tk_success"] = {
        "task_id": "tk_success",
        "status": "queued",
        "progress": 0.0,
        "project_id": 7,
        "preset": "social_9x16",
    }
    await mv._run_async_mix(
        "tk_success",
        body,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    items, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id
    )
    assert total >= 1
    found = [n for n in items if n.type == "video_generated"]
    assert found
    assert found[0].payload["task_id"] == "tk_success"
    assert found[0].payload["project_id"] == 7


# ---------------------------------------------------------------------------
# mix-video failure path
# ---------------------------------------------------------------------------


class _ExplodingPipeline:
    async def run(self, _req):
        raise RuntimeError("clip missing")


async def test_mix_video_failure_creates_notification(
    monkeypatch,
    test_workspace_id: int,
    test_user_id: int,
):
    monkeypatch.setattr(mv, "MixPipeline", lambda: _ExplodingPipeline())
    from app.api.mix_video import MixVideoRequest

    body = MixVideoRequest(
        project_id=8,
        clips=[{"path": "/tmp/missing.mp4"}],
    )
    # _run_async_mix manages the in-memory _TASKS dict — pre-seed the slot.
    mv._TASKS["tk_fail"] = {
        "task_id": "tk_fail",
        "status": "queued",
        "progress": 0.0,
        "project_id": 8,
        "preset": "social_9x16",
    }
    await mv._run_async_mix(
        "tk_fail",
        body,
        workspace_id=test_workspace_id,
        user_id=test_user_id,
    )
    assert mv._TASKS["tk_fail"]["status"] == "failed"

    items, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id
    )
    failed = [n for n in items if n.type == "video_failed"]
    assert failed
    assert "clip missing" in failed[0].message


async def test_mix_video_skips_notify_when_no_workspace_id(
    monkeypatch,
    test_workspace_id: int,
):
    """If the caller didn't set X-Workspace-Id (passes None), no notification
    should be written. Render succeeds either way.
    """
    monkeypatch.setattr(mv, "MixPipeline", lambda: _FakePipeline())
    from app.api.mix_video import MixVideoRequest

    body = MixVideoRequest(project_id=9, clips=[{"path": "/tmp/x.mp4"}])
    mv._TASKS["tk_no_ws"] = {
        "task_id": "tk_no_ws",
        "status": "queued",
        "progress": 0.0,
        "project_id": 9,
        "preset": "social_9x16",
    }
    await mv._run_async_mix(
        "tk_no_ws",
        body,
        workspace_id=None,
        user_id=None,
    )
    assert mv._TASKS["tk_no_ws"]["status"] == "succeeded"
    # Our test workspace must still be empty.
    items, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=None
    )
    assert total == 0


# ---------------------------------------------------------------------------
# brand-kit update → notification
# ---------------------------------------------------------------------------


async def test_brand_kit_update_creates_notification(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    # GET to materialise a default kit
    r0 = client.get("/api/v1/brand-kit", headers=auth_headers)
    assert r0.status_code == 200
    # PUT with a real change
    r = client.put(
        "/api/v1/brand-kit",
        headers=auth_headers,
        json={"primary_color": "#FF00AA", "font_heading": "Helvetica"},
    )
    assert r.status_code == 200, r.text

    items, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id
    )
    drift_notices = [n for n in items if n.type == "brand_kit_changed"]
    assert drift_notices, f"no brand_kit_changed in {[n.type for n in items]}"
    keys = drift_notices[0].payload["changed_keys"]
    assert "primary_color" in keys
    assert "font_heading" in keys


async def test_brand_kit_empty_update_does_not_notify(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    r0 = client.get("/api/v1/brand-kit", headers=auth_headers)
    assert r0.status_code == 200
    r = client.put("/api/v1/brand-kit", headers=auth_headers, json={})
    assert r.status_code == 200
    _items, total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id
    )
    # Empty patch returns early → no notification written.
    assert total == 0


async def test_brand_kit_logo_upload_creates_notification(
    client: TestClient,
    auth_headers: dict[str, str],
    test_workspace_id: int,
    test_user_id: int,
):
    # Materialise the default kit first
    client.get("/api/v1/brand-kit", headers=auth_headers)
    # Build a real 1x1 PNG so the Pillow decode step succeeds
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (1, 1), (255, 0, 0)).save(buf, format="PNG")
    buf.seek(0)

    r = client.post(
        "/api/v1/brand-kit/logo",
        headers=auth_headers,
        files={"file": ("logo.png", buf, "image/png")},
        data={"field": "logo_url"},
    )
    assert r.status_code == 200, r.text
    items, _total, _ = await svc.list_notifications(
        workspace_id=test_workspace_id, user_id=test_user_id
    )
    kit_changes = [n for n in items if n.type == "brand_kit_changed"]
    assert kit_changes
    assert "logo_url" in kit_changes[0].payload["changed_keys"]


# ---------------------------------------------------------------------------
# End-to-end: see the inbox via the public REST API after a brand-kit PUT
# ---------------------------------------------------------------------------


async def test_e2e_brand_kit_update_visible_via_get_notifications(
    client: TestClient,
    auth_headers: dict[str, str],
):
    client.get("/api/v1/brand-kit", headers=auth_headers)
    client.put(
        "/api/v1/brand-kit",
        headers=auth_headers,
        json={"primary_color": "#112233"},
    )
    # Inbox endpoint must show the row created by the trigger
    listing = client.get(
        "/api/v1/notifications?category=drift", headers=auth_headers
    ).json()
    assert listing["total"] >= 1
    assert any(it["type"] == "brand_kit_changed" for it in listing["items"])

    # And unread-count reflects it
    count = client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    ).json()
    assert count["unread"] >= 1
