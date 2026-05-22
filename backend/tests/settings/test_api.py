"""End-to-end REST tests for the Settings module.

These tests exercise:

* Auto-materialise on first GET (no row → fresh defaults).
* Idempotent reads (same row id on the second call).
* PATCH semantics — only supplied keys are written; others untouched.
* Cross-workspace isolation.
* Permission gating on the org/admin endpoints.
* Aggregate ``GET /api/v1/settings`` bundle.
* Cross-validation: ``default_brand_kit_id`` must belong to the workspace.
* App-settings CRUD with public/private read rules.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Profile — GET / PUT
# ---------------------------------------------------------------------------


def test_get_profile_requires_user(isolated_db, workspace_headers):
    """Profile is user-scoped — anonymous calls 401."""
    r = isolated_db.get("/api/v1/settings/profile", headers=workspace_headers)
    assert r.status_code == 401, r.text


def test_get_profile_materialises_defaults(isolated_db, user_headers):
    r = isolated_db.get("/api/v1/settings/profile", headers=user_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_id"] == 42
    assert body["language"] == "zh-CN"
    assert body["timezone"] == "Asia/Shanghai"
    assert body["theme"] == "system"
    assert body["email_notifications_enabled"] is True
    assert body["inbox_digest"] == "weekly"


def test_profile_get_is_idempotent(isolated_db, user_headers):
    a = isolated_db.get("/api/v1/settings/profile", headers=user_headers).json()
    b = isolated_db.get("/api/v1/settings/profile", headers=user_headers).json()
    assert a["user_id"] == b["user_id"]
    # Server-managed timestamps must match — no second materialise happened.
    assert a["created_at"] == b["created_at"]


def test_put_profile_patches_partial(isolated_db, user_headers):
    r = isolated_db.put(
        "/api/v1/settings/profile",
        headers=user_headers,
        json={
            "nickname": "Ava",
            "language": "en-US",
            "theme": "dark",
            "inbox_digest": "daily",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nickname"] == "Ava"
    assert body["language"] == "en-US"
    assert body["theme"] == "dark"
    assert body["inbox_digest"] == "daily"
    # Untouched fields keep their defaults.
    assert body["email_notifications_enabled"] is True
    assert body["sound_enabled"] is False


def test_put_profile_rejects_invalid_timezone(isolated_db, user_headers):
    r = isolated_db.put(
        "/api/v1/settings/profile",
        headers=user_headers,
        json={"timezone": "Unknown/Place"},
    )
    assert r.status_code == 422


def test_put_profile_rejects_unknown_field(isolated_db, user_headers):
    r = isolated_db.put(
        "/api/v1/settings/profile",
        headers=user_headers,
        json={"is_admin": True},
    )
    assert r.status_code == 422


def test_profile_isolates_per_user(isolated_db, workspace_headers):
    h1 = {**workspace_headers, "X-User-Id": "1"}
    h2 = {**workspace_headers, "X-User-Id": "2"}
    isolated_db.put(
        "/api/v1/settings/profile",
        headers=h1,
        json={"nickname": "First", "theme": "dark"},
    )
    isolated_db.put(
        "/api/v1/settings/profile",
        headers=h2,
        json={"nickname": "Second", "theme": "light"},
    )
    a = isolated_db.get("/api/v1/settings/profile", headers=h1).json()
    b = isolated_db.get("/api/v1/settings/profile", headers=h2).json()
    assert a["nickname"] == "First" and a["theme"] == "dark"
    assert b["nickname"] == "Second" and b["theme"] == "light"
    assert a["user_id"] != b["user_id"]


def test_put_profile_empty_body_returns_current(isolated_db, user_headers):
    isolated_db.get("/api/v1/settings/profile", headers=user_headers)
    r = isolated_db.put(
        "/api/v1/settings/profile", headers=user_headers, json={}
    )
    assert r.status_code == 200
    assert r.json()["language"] == "zh-CN"


# ---------------------------------------------------------------------------
# Organization — GET / PUT
# ---------------------------------------------------------------------------


def test_get_org_materialises_defaults(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/settings/organization", headers=workspace_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workspace_id"] == 1
    assert body["region"] == "eu-central-1"
    assert body["default_aspect_ratio"] == "9:16"
    assert body["default_codec"] == "h264"
    assert body["default_loudness_lufs"] == pytest.approx(-14.0)
    assert body["video_watermark_enabled"] is True
    assert body["session_duration_hours"] == 12
    assert body["force_mfa"] is False


def test_put_org_admin_allowed_in_demo_workspace(isolated_db, workspace_headers):
    """In demo workspace (id=1) the role fallback grants admin."""
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={
            "region": "us-east-1",
            "default_codec": "h265",
            "default_loudness_lufs": -16.0,
            "force_mfa": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["region"] == "us-east-1"
    assert body["default_codec"] == "h265"
    assert body["default_loudness_lufs"] == pytest.approx(-16.0)
    assert body["force_mfa"] is True


def test_put_org_rejects_non_admin(isolated_db, member_headers):
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers=member_headers,
        json={"region": "us-east-1"},
    )
    assert r.status_code == 403, r.text


def test_put_org_rejects_guest(isolated_db, guest_headers):
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers=guest_headers,
        json={"region": "us-east-1"},
    )
    assert r.status_code == 403


def test_get_org_open_to_members(isolated_db, member_headers):
    """Members can read org settings even if they can't write."""
    r = isolated_db.get(
        "/api/v1/settings/organization", headers=member_headers
    )
    assert r.status_code == 200


def test_put_org_validates_brand_kit_belongs_to_workspace(
    isolated_db, workspace_headers
):
    """Pointing default_brand_kit_id at a kit from a different workspace
    must 400 — we don't want a fk-less SQLite letting cross-org pollution
    through."""
    # Seed one kit in workspace 1.
    r = isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"primary_color": "#102030"},
    )
    kit_id_ws1 = r.json()["id"]

    # Try to attach it as the default for workspace 2. Non-demo workspaces
    # need an explicit admin role override since the demo-workspace fallback
    # only fires for workspace_id=1.
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers={"X-Workspace-Id": "2", "X-Workspace-Role": "admin"},
        json={"default_brand_kit_id": kit_id_ws1},
    )
    assert r.status_code == 400, r.text
    assert "brand_kit" in r.json()["detail"]


def test_put_org_loudness_out_of_range(isolated_db, workspace_headers):
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"default_loudness_lufs": -100.0},
    )
    assert r.status_code == 422


def test_put_org_notification_prefs_unknown_category(
    isolated_db, workspace_headers
):
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"notification_preferences": {"bogus_category": True}},
    )
    assert r.status_code == 422


def test_org_isolates_workspaces(isolated_db):
    """Two workspaces never see each other's org settings."""
    # Demo workspace (id=1) gets the admin fallback automatically; the
    # secondary workspace needs the role header to write.
    h1 = {"X-Workspace-Id": "1"}
    h2 = {"X-Workspace-Id": "2", "X-Workspace-Role": "admin"}
    isolated_db.put(
        "/api/v1/settings/organization",
        headers=h1,
        json={"region": "eu-central-1"},
    )
    isolated_db.put(
        "/api/v1/settings/organization",
        headers=h2,
        json={"region": "us-east-1"},
    )
    a = isolated_db.get("/api/v1/settings/organization", headers=h1).json()
    b = isolated_db.get(
        "/api/v1/settings/organization", headers={"X-Workspace-Id": "2"}
    ).json()
    assert a["region"] == "eu-central-1"
    assert b["region"] == "us-east-1"
    assert a["workspace_id"] != b["workspace_id"]


# ---------------------------------------------------------------------------
# Aggregate / effective
# ---------------------------------------------------------------------------


def test_get_settings_bundle_with_user(isolated_db, user_headers):
    r = isolated_db.get("/api/v1/settings", headers=user_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile"] is not None
    assert body["profile"]["user_id"] == 42
    assert body["organization"] is not None
    assert body["organization"]["workspace_id"] == 1
    assert body["effective"] is not None
    # ``effective`` mirrors the org defaults straight out of the box.
    assert body["effective"]["aspect_ratio"] == "9:16"
    assert body["effective"]["codec"] == "h264"


def test_get_settings_bundle_no_user_omits_profile(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/settings", headers=workspace_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["profile"] is None
    assert body["organization"] is not None


def test_get_settings_scope_filter(isolated_db, user_headers):
    r = isolated_db.get(
        "/api/v1/settings?scope=organization", headers=user_headers
    )
    body = r.json()
    assert body["profile"] is None
    assert body["organization"] is not None
    assert body["effective"] is None


def test_get_effective_render_defaults(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/settings/effective", headers=workspace_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_id"] == 1
    assert body["aspect_ratio"] == "9:16"
    assert body["codec"] == "h264"
    assert body["watermark_enabled"] is True


def test_effective_reflects_org_changes(isolated_db, workspace_headers):
    isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"default_codec": "h265", "default_loudness_lufs": -16.0},
    )
    body = isolated_db.get(
        "/api/v1/settings/effective", headers=workspace_headers
    ).json()
    assert body["codec"] == "h265"
    assert body["loudness_lufs"] == pytest.approx(-16.0)


# ---------------------------------------------------------------------------
# App settings (global K/V)
# ---------------------------------------------------------------------------


def test_app_setting_create_requires_admin(isolated_db, member_headers):
    r = isolated_db.post(
        "/api/v1/settings/app",
        headers=member_headers,
        json={"key": "render.max_concurrent", "value": 8},
    )
    assert r.status_code == 403


def test_app_setting_create_then_get(isolated_db, workspace_headers):
    r = isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={
            "key": "feature.beta_studio_enabled",
            "value": True,
            "description": "Toggle for the beta studio UI.",
            "is_public": True,
        },
    )
    assert r.status_code == 201, r.text

    r = isolated_db.get(
        "/api/v1/settings/app/feature.beta_studio_enabled",
        headers=workspace_headers,
    )
    body = r.json()
    assert body["value"] is True
    assert body["is_public"] is True


def test_app_setting_duplicate_key_409(isolated_db, workspace_headers):
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "x.y", "value": 1},
    )
    r = isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "x.y", "value": 2},
    )
    assert r.status_code == 409


def test_app_setting_private_blocked_for_member(
    isolated_db, workspace_headers, member_headers
):
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "internal.secret_flag", "value": "x", "is_public": False},
    )
    r = isolated_db.get(
        "/api/v1/settings/app/internal.secret_flag", headers=member_headers
    )
    assert r.status_code == 403


def test_app_setting_public_visible_to_member(
    isolated_db, workspace_headers, member_headers
):
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "marketing.hero", "value": "Ship", "is_public": True},
    )
    r = isolated_db.get(
        "/api/v1/settings/app/marketing.hero", headers=member_headers
    )
    assert r.status_code == 200
    assert r.json()["value"] == "Ship"


def test_app_setting_list_filters_to_public_for_non_admin(
    isolated_db, workspace_headers, member_headers
):
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "marketing.hero", "value": "A", "is_public": True},
    )
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "internal.flag", "value": "B", "is_public": False},
    )

    keys_admin = {
        x["key"]
        for x in isolated_db.get(
            "/api/v1/settings/app?public_only=false", headers=workspace_headers
        ).json()["items"]
    }
    keys_member = {
        x["key"]
        for x in isolated_db.get(
            "/api/v1/settings/app?public_only=false", headers=member_headers
        ).json()["items"]
    }
    assert keys_admin == {"marketing.hero", "internal.flag"}
    assert keys_member == {"marketing.hero"}


def test_app_setting_update_patches_partial(isolated_db, workspace_headers):
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "tune.x", "value": 1, "description": "old"},
    )
    r = isolated_db.put(
        "/api/v1/settings/app/tune.x",
        headers=workspace_headers,
        json={"value": 42},
    )
    body = r.json()
    assert body["value"] == 42
    assert body["description"] == "old"


def test_app_setting_delete(isolated_db, workspace_headers):
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "doomed.flag", "value": True},
    )
    r = isolated_db.delete(
        "/api/v1/settings/app/doomed.flag", headers=workspace_headers
    )
    assert r.status_code == 200
    r = isolated_db.get(
        "/api/v1/settings/app/doomed.flag", headers=workspace_headers
    )
    assert r.status_code == 404


def test_app_setting_delete_requires_admin(isolated_db, member_headers, workspace_headers):
    isolated_db.post(
        "/api/v1/settings/app",
        headers=workspace_headers,
        json={"key": "doomed.flag", "value": True},
    )
    r = isolated_db.delete(
        "/api/v1/settings/app/doomed.flag", headers=member_headers
    )
    assert r.status_code == 403


def test_app_setting_get_missing_404(isolated_db, workspace_headers):
    r = isolated_db.get(
        "/api/v1/settings/app/nope.missing", headers=workspace_headers
    )
    assert r.status_code == 404
