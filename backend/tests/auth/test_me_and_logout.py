"""``GET /auth/me`` and ``POST /auth/logout`` tests."""

from __future__ import annotations

from tests.auth._helpers import auth_headers, register


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


def test_me_returns_user_and_orgs(client):
    body = register(client, email="alice@acme.com")
    headers = auth_headers(body["access_token"])
    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == "alice@acme.com"
    assert data["user"]["username"]  # derived non-empty
    assert len(data["organizations"]) >= 1
    # /me does not re-issue tokens.
    assert data["access_token"] == ""
    assert data["refresh_token"] == ""


def test_me_requires_authentication(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    # 401 carries the OAuth2 Bearer challenge per RFC 6750.
    assert r.headers.get("www-authenticate") == "Bearer"


def test_me_rejects_malformed_token(client):
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.real.jwt"},
    )
    assert r.status_code == 401


def test_me_rejects_refresh_token_as_bearer(client):
    body = register(client, email="bob@acme.com")
    # The Authorization header should reject a refresh token because it
    # carries ``type=refresh``, not ``type=access``.
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['refresh_token']}"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# /logout
# ---------------------------------------------------------------------------


def test_logout_works_without_auth(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body.get("message") == "logged out"


def test_logout_works_with_auth_too(client):
    body = register(client, email="carol@acme.com")
    headers = auth_headers(body["access_token"])
    r = client.post("/api/v1/auth/logout", headers=headers)
    assert r.status_code == 200
    # Token remains *technically* valid (stateless); the contract is that
    # the client drops it. Confirm the token still works post-logout — the
    # next iteration will introduce a deny-list when we want true revocation.
    r2 = client.get("/api/v1/auth/me", headers=headers)
    assert r2.status_code == 200
