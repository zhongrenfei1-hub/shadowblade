"""API Key CRUD + auth tests (10 cases).

Covers:
* Generation: plaintext returned once; matching hash; correct prefix.
* Listing returns masked view (no secret leakage).
* Update is PATCH-style and refuses to mutate scopes.
* Revoke is soft (row remains, ``is_active=False``).
* verify_api_key — happy path, unknown, malformed, revoked, scope mismatch.
* Listing isolation between workspaces.
"""

from __future__ import annotations

import asyncio

import pytest

from app.services.integrations.api_key_service import (
    APIKeyAuthError,
    generate_api_key,
    hash_api_key,
    mask_api_key,
    scope_satisfied,
    verify_api_key,
)


# --------------------------------------------------------------------------- #
# Pure-function tests — no DB needed                                          #
# --------------------------------------------------------------------------- #


def test_generate_api_key_returns_consistent_tuple():
    plaintext, prefix, last_four, key_hash = generate_api_key()
    assert plaintext.startswith(prefix)
    assert plaintext.endswith(last_four)
    assert hash_api_key(plaintext) == key_hash
    # Hash is deterministic + 64 chars (SHA-256 hex)
    assert len(key_hash) == 64


def test_mask_api_key_format():
    assert mask_api_key("sb_test_", "abcd") == "sb_test_•••••abcd"


def test_scope_satisfied_wildcard_wins():
    assert scope_satisfied(["*"], "mix:write") is True
    assert scope_satisfied(["mix:read"], "mix:write") is False
    assert scope_satisfied(["mix:write", "templates:read"], "mix:write") is True


# --------------------------------------------------------------------------- #
# CRUD via TestClient                                                          #
# --------------------------------------------------------------------------- #


def test_create_api_key_returns_plaintext_once(isolated_db, workspace_headers):
    r = isolated_db.post(
        "/api/v1/integrations/api-keys",
        json={"name": "deploy bot", "scopes": ["mix:write", "templates:read"]},
        headers=workspace_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    # Plaintext is present
    assert data["key"].startswith(("sb_live_", "sb_test_"))
    assert data["masked"].endswith(data["last_four"])
    assert data["scopes"] == ["mix:write", "templates:read"]

    # GET list never returns plaintext
    r2 = isolated_db.get("/api/v1/integrations/api-keys", headers=workspace_headers)
    assert r2.status_code == 200
    items = r2.json()["items"]
    assert len(items) == 1
    assert "key" not in items[0]
    assert items[0]["masked"] == data["masked"]


def test_create_api_key_rejects_empty_scopes(isolated_db, workspace_headers):
    r = isolated_db.post(
        "/api/v1/integrations/api-keys",
        json={"name": "bad", "scopes": []},
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_create_api_key_rejects_unknown_scope(isolated_db, workspace_headers):
    r = isolated_db.post(
        "/api/v1/integrations/api-keys",
        json={"name": "bad", "scopes": ["fake:scope"]},
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_patch_api_key_updates_name_and_active(isolated_db, workspace_headers, api_key_factory):
    _, body = api_key_factory(name="orig")
    key_id = body["id"]

    r = isolated_db.patch(
        f"/api/v1/integrations/api-keys/{key_id}",
        json={"name": "renamed", "is_active": False},
        headers=workspace_headers,
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["name"] == "renamed"
    assert out["is_active"] is False


def test_patch_api_key_refuses_scope_mutation(isolated_db, workspace_headers, api_key_factory):
    _, body = api_key_factory(name="orig", scopes=["mix:read"])
    key_id = body["id"]
    # Scopes is NOT in ApiKeyUpdate — should 422
    r = isolated_db.patch(
        f"/api/v1/integrations/api-keys/{key_id}",
        json={"scopes": ["mix:write"]},
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_revoke_api_key_is_soft(isolated_db, workspace_headers, api_key_factory):
    _, body = api_key_factory()
    key_id = body["id"]
    r = isolated_db.delete(
        f"/api/v1/integrations/api-keys/{key_id}", headers=workspace_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is False

    # Row still listable, just inactive
    r2 = isolated_db.get("/api/v1/integrations/api-keys", headers=workspace_headers)
    item = r2.json()["items"][0]
    assert item["is_active"] is False


def test_get_api_key_404_for_unknown(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/integrations/api-keys/99999", headers=workspace_headers)
    assert r.status_code == 404


def test_workspace_isolation(isolated_db, api_key_factory):
    _, body = api_key_factory(name="ws1-key")  # workspace 1
    # workspace 2 can't see it
    r = isolated_db.get(
        "/api/v1/integrations/api-keys",
        headers={"X-Workspace-Id": "2"},
    )
    assert r.status_code == 200
    assert r.json()["items"] == []
    # And cannot delete it either
    r2 = isolated_db.delete(
        f"/api/v1/integrations/api-keys/{body['id']}",
        headers={"X-Workspace-Id": "2"},
    )
    assert r2.status_code == 404


# --------------------------------------------------------------------------- #
# verify_api_key against the real DB                                          #
# --------------------------------------------------------------------------- #


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_verify_api_key_rejects_malformed(isolated_db):
    from app.core.db import SessionLocal

    async def _check():
        async with SessionLocal() as db:
            with pytest.raises(APIKeyAuthError):
                await verify_api_key(db, plaintext="not-a-real-key")
            with pytest.raises(APIKeyAuthError):
                await verify_api_key(db, plaintext="")

    asyncio.run(_check())


def test_verify_api_key_happy_and_scoped(isolated_db, api_key_factory):
    from app.core.db import SessionLocal

    plaintext, body = api_key_factory(scopes=["mix:write"])

    async def _check():
        async with SessionLocal() as db:
            result = await verify_api_key(
                db, plaintext=plaintext, required_scope="mix:write"
            )
            assert result.api_key_id == body["id"]
            assert result.workspace_id == 1
            assert "mix:write" in result.scopes

            # Scope mismatch → 403
            with pytest.raises(APIKeyAuthError) as exc_info:
                await verify_api_key(
                    db, plaintext=plaintext, required_scope="brand-kit:write"
                )
            assert exc_info.value.status_code == 403

    asyncio.run(_check())


def test_verify_api_key_after_revoke_is_403(isolated_db, workspace_headers, api_key_factory):
    from app.core.db import SessionLocal

    plaintext, body = api_key_factory(scopes=["*"])

    # Revoke through the HTTP layer (exercises the full flow)
    isolated_db.delete(
        f"/api/v1/integrations/api-keys/{body['id']}", headers=workspace_headers
    )

    async def _check():
        async with SessionLocal() as db:
            with pytest.raises(APIKeyAuthError) as exc_info:
                await verify_api_key(db, plaintext=plaintext)
            assert exc_info.value.status_code == 403

    asyncio.run(_check())
