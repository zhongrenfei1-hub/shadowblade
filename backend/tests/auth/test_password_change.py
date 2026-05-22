"""Password-change endpoint tests — ``POST /api/v1/auth/password/change``.

Authenticated rotation flow. Covers the require-current-password defence,
new-password validation, and the audit timestamp side-effect.
"""

from __future__ import annotations

from tests.auth._helpers import auth_headers, login, register


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_change_password_rotates_and_old_pw_stops_working(client):
    body = register(client, email="alice@acme.com", password="oldpassword1")
    headers = auth_headers(body["access_token"])
    r = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "oldpassword1", "new_password": "newpassword1"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Old password no longer logs in.
    r2 = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@acme.com", "password": "oldpassword1"},
    )
    assert r2.status_code == 401

    # New password logs in successfully.
    fresh = login(client, email_or_username="alice@acme.com", password="newpassword1")
    assert fresh["user"]["email"] == "alice@acme.com"


def test_change_password_updates_last_password_change_at(client):
    body = register(client, email="bob@acme.com", password="oldpassword1")
    before = body["user"]["last_password_change_at"]
    headers = auth_headers(body["access_token"])
    client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "oldpassword1", "new_password": "newpassword1"},
        headers=headers,
    )
    me = client.get("/api/v1/auth/me", headers=headers).json()
    after = me["user"]["last_password_change_at"]
    assert after is not None
    if before is not None:
        assert after >= before


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_change_password_requires_authentication(client):
    r = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "x", "new_password": "y" * 10},
    )
    assert r.status_code == 401


def test_change_password_rejects_wrong_current(client):
    body = register(client, email="carol@acme.com", password="rightpass1")
    headers = auth_headers(body["access_token"])
    r = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "WRONGpass1", "new_password": "newpassword1"},
        headers=headers,
    )
    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"]


def test_change_password_rejects_no_op_rotation(client):
    body = register(client, email="diana@acme.com", password="samepass1")
    headers = auth_headers(body["access_token"])
    r = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "samepass1", "new_password": "samepass1"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "differ" in r.json()["detail"]


def test_change_password_rejects_short_new_password(client):
    body = register(client, email="ed@acme.com", password="oldpassword1")
    headers = auth_headers(body["access_token"])
    r = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "oldpassword1", "new_password": "short"},
        headers=headers,
    )
    assert r.status_code == 422


def test_change_password_rejects_oversize_new_password(client):
    body = register(client, email="fred@acme.com", password="oldpassword1")
    headers = auth_headers(body["access_token"])
    r = client.post(
        "/api/v1/auth/password/change",
        json={
            "current_password": "oldpassword1",
            "new_password": "a" * 73,  # > 72 bytes
        },
        headers=headers,
    )
    assert r.status_code == 422


def test_change_password_does_not_invalidate_existing_tokens(client):
    # Stateless JWT design — until we add revocation tracking, an issued
    # access token survives password rotation. This test pins that
    # behaviour so future work that *changes* it has to update the test.
    body = register(client, email="gina@acme.com", password="oldpassword1")
    headers = auth_headers(body["access_token"])
    client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "oldpassword1", "new_password": "newpassword1"},
        headers=headers,
    )
    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
