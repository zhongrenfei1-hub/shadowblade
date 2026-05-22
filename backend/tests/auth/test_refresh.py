"""Refresh-token endpoint tests — ``POST /api/v1/auth/refresh``.

Coverage:

* rotation semantics (new pair returned, both valid)
* type-check (access token rejected as refresh)
* expired / malformed inputs
* user-disable invalidates the refresh path
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from sqlalchemy import update

from app.core.config import settings
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.models import User
from tests.auth._helpers import auth_headers, register


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_refresh_returns_new_pair(client):
    body = register(client, email="alice@acme.com")
    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["access_token"]
    assert data["refresh_token"]
    # Rotation: the new refresh must differ from the old one.
    assert data["refresh_token"] != body["refresh_token"]


def test_refresh_new_access_token_is_usable_on_me(client):
    body = register(client, email="bob@acme.com")
    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    ).json()
    r = client.get(
        "/api/v1/auth/me", headers=auth_headers(refreshed["access_token"])
    )
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "bob@acme.com"


def test_refresh_new_refresh_token_is_usable_again(client):
    body = register(client, email="carol@acme.com")
    first = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    ).json()
    second = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert second.status_code == 200
    # And the *new* token differs again.
    assert second.json()["refresh_token"] != first["refresh_token"]


def test_refresh_preserves_workspace_claim(client):
    body = register(client, email="diana@acme.com")
    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    ).json()
    claims = decode_access_token(refreshed["access_token"])
    # Workspace claim was carried over (refresh recomputed it from DB).
    assert claims.get("ws") == body["default_workspace_id"]


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_refresh_rejects_access_token(client):
    body = register(client, email="ed@acme.com")
    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["access_token"]},  # access, not refresh
    )
    assert r.status_code == 401


def test_refresh_rejects_garbage(client):
    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not.a.valid.jwt"},
    )
    assert r.status_code == 401


def test_refresh_rejects_expired_token(client):
    body = register(client, email="fred@acme.com")
    user_id = body["user"]["id"]
    # Mint a manually-expired refresh token using the same secret/algo.
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int((now - timedelta(hours=1)).timestamp()),
        "exp": int((now - timedelta(minutes=1)).timestamp()),
        "type": REFRESH_TOKEN_TYPE,
        "jti": "expired-test",
    }
    expired = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired},
    )
    assert r.status_code == 401


def test_refresh_rejects_wrong_signature(client):
    body = register(client, email="gina@acme.com")
    user_id = body["user"]["id"]
    # Sign with a different secret — must fail verification.
    bad = jwt.encode(
        {
            "sub": str(user_id),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(
                (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
            ),
            "type": REFRESH_TOKEN_TYPE,
            "jti": "wrong-key-test",
        },
        "this-is-a-different-secret-entirely",
        algorithm=settings.jwt_algorithm,
    )
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": bad})
    assert r.status_code == 401


def test_refresh_rejects_disabled_user(client, db_engine):
    body = register(client, email="hank@acme.com")
    # Flip the user's is_active flag — simulates the user being disabled
    # mid-session.
    engine, factory = db_engine

    import anyio

    async def _disable():
        async with factory() as session:
            await session.execute(
                update(User)
                .where(User.id == body["user"]["id"])
                .values(is_active=False)
            )
            await session.commit()

    anyio.run(_disable)

    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert r.status_code == 401


def test_refresh_rejects_unknown_user(client):
    # Refresh token for a user that never existed.
    forged = create_refresh_token(999_999)
    r = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": forged}
    )
    assert r.status_code == 401


def test_refresh_rejects_missing_body_field(client):
    r = client.post("/api/v1/auth/refresh", json={})
    assert r.status_code == 422


def test_refresh_rejects_empty_string(client):
    r = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": ""}
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Unit-level checks for the helpers (no HTTP round-trip)
# ---------------------------------------------------------------------------


def test_create_refresh_token_roundtrips():
    token = create_refresh_token(42)
    claims = decode_refresh_token(token)
    assert claims["sub"] == "42"
    assert claims["type"] == "refresh"
    # bcrypt is unused here, but keep the import live to catch a silent
    # ImportError when modules are pruned.
    assert bcrypt is not None
