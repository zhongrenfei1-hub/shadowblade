"""Auth endpoint tests — register, login, /me, logout.

Covers the password rules, JWT round-trip, duplicate-email handling, and
the personal-workspace bootstrap that happens on register.
"""

from __future__ import annotations

import pytest

from tests.organizations.conftest import login, register


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


def test_register_creates_user_and_personal_workspace(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ava@acme.com",
            "full_name": "Ava Chen",
            "password": "supersecret1",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "ava@acme.com"
    assert body["user"]["full_name"] == "Ava Chen"
    assert body["user"]["is_active"] is True
    assert body["user"]["id"] > 0
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["new_organization_id"] == body["default_workspace_id"]
    # The personal workspace lists the user with role=owner.
    assert any(o["role"] == "owner" for o in body["organizations"])


def test_register_rejects_duplicate_email(client):
    register(client, email="dup@acme.com")
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "DUP@acme.com",  # different case — must still collide
            "full_name": "Other",
            "password": "anotherpass1",
        },
    )
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_register_password_too_short(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@y.com",
            "full_name": "X",
            "password": "short",  # < 8 chars
        },
    )
    assert r.status_code == 422


def test_register_password_too_long_bytes(client):
    # 73 chars of ASCII = 73 bytes > 72-byte bcrypt cap
    long_pw = "a" * 73
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@y.com",
            "full_name": "X",
            "password": long_pw,
        },
    )
    assert r.status_code == 422


def test_register_rejects_invalid_email(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "full_name": "X", "password": "validpass1"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_with_correct_credentials(client):
    register(
        client, email="bob@acme.com", password="hunter2hunter",
        drop_personal_ws=False,
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@acme.com", "password": "hunter2hunter"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["email"] == "bob@acme.com"
    assert body["default_workspace_id"] is not None
    assert len(body["organizations"]) >= 1


def test_login_wrong_password_is_401(client):
    register(client, email="carol@acme.com", password="rightpass1")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@acme.com", "password": "wrongpass1"},
    )
    assert r.status_code == 401
    assert "invalid credentials" in r.json()["detail"]


def test_login_unknown_email_is_401_same_message(client):
    # Same error as wrong-password — must not leak existence.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "noone@acme.com", "password": "whatever1"},
    )
    assert r.status_code == 401
    assert "invalid credentials" in r.json()["detail"]


def test_login_oauth2_form_flow(client):
    register(client, email="dora@acme.com", password="hunter2hunter")
    # OAuth2 password flow uses ``username`` not ``email``.
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "dora@acme.com", "password": "hunter2hunter"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_email_is_case_insensitive(client):
    register(client, email="emma@acme.com")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "EMMA@ACME.COM", "password": "strongpass1"},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate") == "Bearer"


def test_me_returns_user_and_orgs(client):
    h = register(client, email="frank@acme.com", drop_personal_ws=False)
    r = client.get("/api/v1/auth/me", headers=h["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "frank@acme.com"
    assert len(body["organizations"]) >= 1
    # /me never re-issues a token.
    assert body["access_token"] == ""


def test_me_with_invalid_token_is_401(client):
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.a.real.jwt"},
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_is_stateless(client):
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    # The new MessageResponse shape also carries a message field. Older
    # clients that only check ``ok`` keep working unchanged.
    assert body.get("message") == "logged out"
