"""End-to-end tests for the Brand Kit REST endpoints.

These tests hit the FastAPI app via :class:`TestClient`, so they cover:
- routing (GET / PUT / POST + plural fallbacks)
- Depends chain (workspace + user header resolution)
- DB round-trip through SQLAlchemy
- hex validation kicking in at the Pydantic boundary
- file upload + Pillow decode + storage path mapping

The ``isolated_db`` fixture rebuilds the engine against a temp SQLite
database so tests never touch the dev ``shadowblade.db``.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image


# --- GET /brand-kit ---------------------------------------------------------


def test_get_returns_defaults_for_empty_workspace(isolated_db, workspace_headers):
    """First read materialises a workspace-scoped default kit on the fly."""
    r = isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scope"] == "workspace"
    assert body["workspace_id"] == 1
    assert body["primary_color"] == "#0F2A4A"
    assert body["accent_color"] == "#22D3B7"
    assert body["secondary_color"] == "#F5F7FB"
    assert body["watermark_position"] == "br"
    assert body["watermark_opacity"] == pytest.approx(0.78)
    assert body["is_active"] is True
    assert body["target_lufs"] == pytest.approx(-14.0)


def test_get_is_idempotent(isolated_db, workspace_headers):
    """Second GET returns the same kit — not a duplicate row."""
    r1 = isolated_db.get("/api/v1/brand-kit", headers=workspace_headers).json()
    r2 = isolated_db.get("/api/v1/brand-kit", headers=workspace_headers).json()
    assert r1["id"] == r2["id"]
    # List should also show exactly one row.
    listed = isolated_db.get("/api/v1/brand-kits", headers=workspace_headers).json()
    assert len(listed["items"]) == 1


def test_user_scope_falls_back_to_workspace(isolated_db, user_headers, workspace_headers):
    """A user with no user-scoped kit gets the workspace one."""
    isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    body = isolated_db.get("/api/v1/brand-kit", headers=user_headers).json()
    assert body["scope"] == "workspace"
    assert body["owner_id"] is None


# --- PUT /brand-kit ---------------------------------------------------------


def test_put_patches_color_fields(isolated_db, workspace_headers):
    r = isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"primary_color": "#101728", "accent_color": "#ff7849"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["primary_color"] == "#101728"
    assert body["accent_color"] == "#FF7849"  # canonicalised to upper-case


def test_put_only_modifies_supplied_fields(isolated_db, workspace_headers):
    isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"primary_color": "#101728"},
    )
    after = isolated_db.get("/api/v1/brand-kit", headers=workspace_headers).json()
    assert after["primary_color"] == "#101728"
    # untouched fields stayed on defaults
    assert after["accent_color"] == "#22D3B7"
    assert after["watermark_position"] == "br"


def test_put_rejects_invalid_hex(isolated_db, workspace_headers):
    r = isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"primary_color": "rebeccapurple"},
    )
    assert r.status_code == 422, r.text


def test_put_rejects_out_of_range_opacity(isolated_db, workspace_headers):
    r = isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"watermark_opacity": 1.4},
    )
    assert r.status_code == 422


def test_put_accepts_full_payload(isolated_db, workspace_headers):
    full = {
        "name": "Acme · Spring",
        "primary_color": "#101728",
        "secondary_color": "#ffffff",
        "accent_color": "#ff7849",
        "watermark_text": "@acme",
        "watermark_position": "tl",
        "watermark_opacity": 0.6,
        "watermark_width_pct": 0.2,
        "target_lufs": -16.0,
        "subtitle_size": 72,
        "default_template_name": "product-demo",
        "custom_css_snippet": "/* nothing here */",
    }
    r = isolated_db.put(
        "/api/v1/brand-kit", headers=workspace_headers, json=full
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["name"] == "Acme · Spring"
    assert out["watermark_text"] == "@acme"
    assert out["secondary_color"] == "#FFFFFF"
    assert out["default_template_name"] == "product-demo"


def test_put_with_empty_body_returns_current(isolated_db, workspace_headers):
    """No keys in body → no diff, but should still return the current kit."""
    isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    r = isolated_db.put("/api/v1/brand-kit", headers=workspace_headers, json={})
    assert r.status_code == 200
    assert r.json()["primary_color"] == "#0F2A4A"


def test_put_isolates_workspaces(isolated_db):
    """Two workspaces never see each other's kits."""
    isolated_db.put(
        "/api/v1/brand-kit",
        headers={"X-Workspace-Id": "1"},
        json={"primary_color": "#101728"},
    )
    isolated_db.put(
        "/api/v1/brand-kit",
        headers={"X-Workspace-Id": "2"},
        json={"primary_color": "#FFFFFF"},
    )
    ws1 = isolated_db.get(
        "/api/v1/brand-kit", headers={"X-Workspace-Id": "1"}
    ).json()
    ws2 = isolated_db.get(
        "/api/v1/brand-kit", headers={"X-Workspace-Id": "2"}
    ).json()
    assert ws1["primary_color"] == "#101728"
    assert ws2["primary_color"] == "#FFFFFF"
    assert ws1["id"] != ws2["id"]


# --- POST /brand-kit/logo ---------------------------------------------------


def test_logo_upload_attaches_url(isolated_db, workspace_headers, png_bytes):
    files = {"file": ("brand-logo.png", png_bytes, "image/png")}
    r = isolated_db.post(
        "/api/v1/brand-kit/logo",
        headers=workspace_headers,
        files=files,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("/static/storage/")
    assert body["url"].endswith(".png")
    assert body["bytes"] == len(png_bytes)
    assert body["content_type"] == "image/png"
    assert body["width"] == 1 and body["height"] == 1

    # The kit row should now carry the URL.
    after = isolated_db.get(
        "/api/v1/brand-kit", headers=workspace_headers
    ).json()
    assert after["logo_url"] == body["url"]


def test_logo_upload_rejects_unsupported_extension(
    isolated_db, workspace_headers, png_bytes
):
    files = {"file": ("brand.bmp", png_bytes, "image/bmp")}
    r = isolated_db.post(
        "/api/v1/brand-kit/logo",
        headers=workspace_headers,
        files=files,
    )
    assert r.status_code == 415, r.text


def test_logo_upload_rejects_unknown_field(isolated_db, workspace_headers, png_bytes):
    files = {"file": ("brand.png", png_bytes, "image/png")}
    r = isolated_db.post(
        "/api/v1/brand-kit/logo",
        headers=workspace_headers,
        data={"field": "tagline"},
        files=files,
    )
    assert r.status_code == 400, r.text


def test_logo_upload_field_routing_intro_url(
    isolated_db, workspace_headers, png_bytes
):
    """``field=intro_url`` writes to a different slot, leaving logo_url empty."""
    files = {"file": ("intro.png", png_bytes, "image/png")}
    r = isolated_db.post(
        "/api/v1/brand-kit/logo",
        headers=workspace_headers,
        data={"field": "intro_url"},
        files=files,
    )
    assert r.status_code == 200
    after = isolated_db.get(
        "/api/v1/brand-kit", headers=workspace_headers
    ).json()
    assert after["intro_url"] is not None
    assert after["logo_url"] is None


def test_logo_upload_rejects_corrupt_image(isolated_db, workspace_headers):
    files = {"file": ("broken.png", b"not really a png", "image/png")}
    r = isolated_db.post(
        "/api/v1/brand-kit/logo",
        headers=workspace_headers,
        files=files,
    )
    assert r.status_code == 400, r.text


def test_logo_upload_with_larger_pillow_decoded(isolated_db, workspace_headers):
    """A real Pillow-rendered PNG roundtrips with width/height populated."""
    buf = io.BytesIO()
    img = Image.new("RGB", (320, 200), color=(15, 42, 74))
    img.save(buf, format="PNG")
    files = {"file": ("acme.png", buf.getvalue(), "image/png")}
    r = isolated_db.post(
        "/api/v1/brand-kit/logo", headers=workspace_headers, files=files
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["width"] == 320
    assert body["height"] == 200


# --- Plural / legacy --------------------------------------------------------


def test_post_creates_second_kit(isolated_db, workspace_headers):
    """Workspace can carry more than one kit (e.g. event-specific palettes)."""
    isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)  # default
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=workspace_headers,
        json={"name": "Field Event", "primary_color": "#FF7849"},
    )
    assert r.status_code == 201, r.text
    listed = isolated_db.get(
        "/api/v1/brand-kits", headers=workspace_headers
    ).json()
    assert len(listed["items"]) == 2


def test_delete_deactivates_kit(isolated_db, workspace_headers):
    isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=workspace_headers,
        json={"name": "Outgoing", "primary_color": "#FF7849"},
    )
    kit_id = r.json()["id"]
    r = isolated_db.delete(
        f"/api/v1/brand-kits/{kit_id}", headers=workspace_headers
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False
    # Active resolver should NOT pick the deactivated one.
    active = isolated_db.get(
        "/api/v1/brand-kit", headers=workspace_headers
    ).json()
    assert active["id"] != kit_id


def test_delete_returns_404_for_missing(isolated_db, workspace_headers):
    r = isolated_db.delete("/api/v1/brand-kits/9999", headers=workspace_headers)
    assert r.status_code == 404
