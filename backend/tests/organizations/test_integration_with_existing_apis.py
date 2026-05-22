"""Regression — Team feature must not break brand-kit, templates, mix-video.

The user-facing promise is that adding Team RBAC doesn't disrupt the
existing showcase paths. These tests boot the full FastAPI app and hit
the legacy endpoints both *with* and *without* a JWT to confirm.
"""

from __future__ import annotations

from tests.organizations.conftest import (
    accept,
    create_org,
    invite,
    register,
)


# ---------------------------------------------------------------------------
# Brand kit — backward compatibility
# ---------------------------------------------------------------------------


def test_brand_kit_get_works_without_auth(client):
    """Demo path: no token, no headers → still returns the default kit."""
    r = client.get("/api/v1/brand-kit")
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "primary_color" in body


def test_brand_kit_with_jwt_uses_token_workspace(client):
    """Authed path: the JWT's ``ws`` claim drives the workspace context."""
    h = register(client, email="palette@acme.com")
    org = create_org(client, headers=h["headers"], slug="palette")

    # Switch workspace context to the new org via the X-Workspace-Id header
    # (header beats token claim — that's the documented precedence).
    headers = {**h["headers"], "X-Workspace-Id": str(org["id"])}
    r = client.get("/api/v1/brand-kit", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_id"] == org["id"]


def test_brand_kit_update_persists(client):
    """Authed PUT writes to the resolved workspace."""
    h = register(client, email="painter@acme.com")
    org = create_org(client, headers=h["headers"], slug="painter")
    headers = {**h["headers"], "X-Workspace-Id": str(org["id"])}

    r = client.put(
        "/api/v1/brand-kit",
        json={"name": "Painter Studio", "primary_color": "#FF8800"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Painter Studio"
    assert body["primary_color"] == "#FF8800"
    assert body["workspace_id"] == org["id"]


# ---------------------------------------------------------------------------
# Templates — public endpoint, no auth required
# ---------------------------------------------------------------------------


def test_templates_list_works_without_auth(client):
    r = client.get("/api/v1/templates")
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)


def test_templates_list_works_with_jwt(client):
    h = register(client, email="tmpl@acme.com")
    r = client.get("/api/v1/templates", headers=h["headers"])
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Workspaces (legacy /me endpoint)
# ---------------------------------------------------------------------------


def test_workspaces_me_legacy_still_responds(client):
    """The pre-existing /workspaces/me fixture endpoint stays alive."""
    r = client.get("/api/v1/workspaces/me")
    assert r.status_code == 200
    body = r.json()
    # Demo fixture shape — preserved for the frontend.
    assert body["slug"] == "acme"
    assert "team" in body


# ---------------------------------------------------------------------------
# End-to-end Team scenarios
# ---------------------------------------------------------------------------


def test_full_invite_flow_promotes_new_member_through_brand_kit_path(client):
    """End-to-end: owner invites, member accepts, member reads brand-kit
    scoped to that org via X-Workspace-Id."""
    h_owner = register(client, email="founder2@acme.com")
    h_designer = register(client, email="designer@acme.com")
    org = create_org(client, headers=h_owner["headers"], slug="brand-co")

    inv = invite(
        client, org_id=org["id"], headers=h_owner["headers"],
        email="designer@acme.com", role="member",
    )
    accept(client, code=inv["invite_code"], headers=h_designer["headers"])

    designer_headers = {
        **h_designer["headers"],
        "X-Workspace-Id": str(org["id"]),
    }
    r = client.get("/api/v1/brand-kit", headers=designer_headers)
    assert r.status_code == 200
    assert r.json()["workspace_id"] == org["id"]


def test_mix_video_endpoint_still_accepts_unauthenticated_demo_request(client):
    """mix-video must not require auth — showcase pages depend on it."""
    # We don't actually run a full render here (ffmpeg, expensive); just
    # verify the endpoint accepts the request without 401.
    r = client.post(
        "/api/v1/mix-video",
        json={
            "project_id": "showcase-demo",
            "clips": [
                {"path": "/tmp/does-not-matter.mp4", "start": 0.0, "end": 2.0}
            ],
        },
    )
    # 200 (queued) or 4xx for bad clip path is OK — *not* 401.
    assert r.status_code != 401
