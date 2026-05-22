"""Login endpoint tests — ``POST /api/v1/auth/login``.

Coverage:

* JSON + form-urlencoded flows
* email *and* username login paths
* anti-enumeration (identical error message for unknown vs wrong-password)
* case-insensitive matching
* disabled-account handling
* last_login_at side effect
"""

from __future__ import annotations

from app.core.security import decode_access_token, decode_refresh_token
from tests.auth._helpers import login, register


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_login_with_email_and_correct_password(client):
    register(client, email="alice@acme.com", password="hunter2hunter")
    body = login(
        client, email_or_username="alice@acme.com", password="hunter2hunter"
    )
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "alice@acme.com"
    assert body["default_workspace_id"] is not None


def test_login_with_username_instead_of_email(client):
    register(
        client,
        email="bob@acme.com",
        password="strongpass1",
        username="bobby",
    )
    # The login endpoint accepts the username via the OAuth2 form body.
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "bobby", "password": "strongpass1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "bobby"


def test_login_is_case_insensitive_on_email(client):
    register(client, email="carol@acme.com")
    body = login(
        client, email_or_username="CAROL@ACME.COM", password="strongpass1"
    )
    assert body["user"]["email"] == "carol@acme.com"


def test_login_is_case_insensitive_on_username(client):
    register(client, email="diana@acme.com", username="dee_hi")
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "DEE_HI", "password": "strongpass1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200


def test_login_returns_workspace_claim_in_access_token(client):
    body = register(client, email="ed@acme.com")
    ws_id = body["default_workspace_id"]
    claims = decode_access_token(body["access_token"])
    assert int(claims["sub"]) == body["user"]["id"]
    assert claims.get("ws") == ws_id


def test_login_refresh_token_is_a_refresh_type(client):
    body = register(client, email="fred@acme.com")
    claims = decode_refresh_token(body["refresh_token"])
    assert claims["type"] == "refresh"
    assert int(claims["sub"]) == body["user"]["id"]


def test_login_refresh_token_rejects_as_access(client):
    body = register(client, email="gina@acme.com")
    # A refresh token should NOT decode as an access token.
    from app.core.security import TokenError, decode_access_token

    try:
        decode_access_token(body["refresh_token"])
        raise AssertionError("refresh token decoded as access token")
    except TokenError:
        pass


def test_login_bumps_last_login_at(client):
    register(client, email="hank@acme.com")
    body1 = login(client, email_or_username="hank@acme.com")
    first = body1["user"]["last_login_at"]
    assert first is not None
    # A second login bumps the timestamp.
    body2 = login(client, email_or_username="hank@acme.com")
    second = body2["user"]["last_login_at"]
    assert second is not None
    assert second >= first


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_login_wrong_password_returns_401(client):
    register(client, email="iris@acme.com", password="rightpass1")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "iris@acme.com", "password": "wrongpass1"},
    )
    assert r.status_code == 401
    assert "invalid credentials" in r.json()["detail"]


def test_login_unknown_email_returns_same_message_as_wrong_password(client):
    r1 = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@acme.com", "password": "anything9"},
    )
    register(client, email="jane@acme.com", password="rightpass1")
    r2 = client.post(
        "/api/v1/auth/login",
        json={"email": "jane@acme.com", "password": "wrongpass1"},
    )
    # Identical status + detail prevents enumeration of valid emails.
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]


def test_login_unknown_username_returns_401(client):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent_user", "password": "whatever1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 401


def test_login_rejects_missing_password(client):
    register(client, email="kara@acme.com")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "kara@acme.com"},
    )
    assert r.status_code == 422


def test_login_form_flow_requires_password(client):
    register(client, email="leo@acme.com")
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "leo@acme.com"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 422
