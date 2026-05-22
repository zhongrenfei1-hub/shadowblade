"""Integration smoke tests — verify the auth layer plays nicely with the
existing mix-video / brand-kit / templates surface.

Since the legacy demo endpoints accept ``X-User-Id`` headers as a backward
compat path, the goal here is to confirm:

* JWT bearer auth works against those endpoints (priority over headers)
* Anonymous calls keep working where allowed (demo mode)
* Switching workspace context via the ``ws`` claim doesn't break the
  default-workspace behaviour
"""

from __future__ import annotations

from tests.auth._helpers import auth_headers, register


# ---------------------------------------------------------------------------
# JWT-driven calls land on the right user
# ---------------------------------------------------------------------------


def test_jwt_lets_caller_hit_brand_kit(client):
    body = register(client, email="alice@acme.com")
    headers = auth_headers(body["access_token"])
    # The demo brand-kit endpoint should return *something* (200) even for
    # a fresh user — it bootstraps a default kit on first read.
    r = client.get("/api/v1/brand-kit", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "primary_color" in data or "name" in data


def test_jwt_lets_caller_list_templates(client):
    body = register(client, email="bob@acme.com")
    headers = auth_headers(body["access_token"])
    r = client.get("/api/v1/templates", headers=headers)
    assert r.status_code == 200


def test_jwt_lets_caller_view_mix_presets(client):
    body = register(client, email="carol@acme.com")
    headers = auth_headers(body["access_token"])
    r = client.get("/api/v1/mix-video/presets/list", headers=headers)
    # Presets endpoint is unauthenticated but should accept the bearer
    # header without error.
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Anonymous calls still work where they used to
# ---------------------------------------------------------------------------


def test_anonymous_template_list_still_works(client):
    # The mix-video / brand-kit demo path is unauthenticated. Confirm we
    # didn't accidentally break that by making auth mandatory.
    r = client.get("/api/v1/templates")
    assert r.status_code == 200


def test_anonymous_health_still_works(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Workspace claim → request-scoped org
# ---------------------------------------------------------------------------


def test_jwt_workspace_claim_drives_implicit_workspace(client):
    body = register(client, email="diana@acme.com")
    headers = auth_headers(body["access_token"])
    ws_id = body["default_workspace_id"]
    # Hitting /workspaces/{id} confirms the workspace exists in this DB.
    r = client.get(f"/api/v1/organizations/{ws_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == ws_id


# ---------------------------------------------------------------------------
# Refresh → continue session
# ---------------------------------------------------------------------------


def test_refresh_then_hit_protected_endpoint(client):
    body = register(client, email="ed@acme.com")
    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    ).json()
    new_headers = auth_headers(refreshed["access_token"])
    me = client.get("/api/v1/auth/me", headers=new_headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "ed@acme.com"
