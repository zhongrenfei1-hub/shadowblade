"""Register endpoint tests — ``POST /api/v1/auth/register``.

Coverage spans:

* happy-path with explicit + derived username
* validation errors on email, password, username
* collision handling for both email and username
* response shape (token pair, user record, org bootstrap)
"""

from __future__ import annotations

from tests.auth._helpers import register


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_register_returns_token_pair_and_user(client):
    body = register(
        client,
        email="alice@acme.com",
        full_name="Alice",
        password="strongpass1",
    )
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["access_token"] != body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["refresh_expires_in"] > body["expires_in"]
    assert body["user"]["email"] == "alice@acme.com"
    assert body["user"]["full_name"] == "Alice"
    assert body["user"]["is_active"] is True
    assert body["user"]["is_verified"] is False


def test_register_creates_personal_workspace(client):
    body = register(client, email="bob@acme.com")
    assert body["new_organization_id"] is not None
    assert body["default_workspace_id"] == body["new_organization_id"]
    assert any(o["role"] == "owner" for o in body["organizations"])


def test_register_returns_email_verification_token_in_dev(client):
    body = register(client, email="carol@acme.com")
    # In test mode (environment != "production") the dev token is exposed.
    assert body["email_verification_token"]
    assert isinstance(body["email_verification_token"], str)
    assert len(body["email_verification_token"]) > 20  # JWT-ish


# ---------------------------------------------------------------------------
# Username handling
# ---------------------------------------------------------------------------


def test_register_derives_username_from_email_when_not_provided(client):
    body = register(client, email="diana.smith@acme.com")
    assert body["user"]["username"] == "diana.smith"


def test_register_accepts_explicit_username(client):
    body = register(
        client,
        email="ed@acme.com",
        username="ed_writer",
    )
    assert body["user"]["username"] == "ed_writer"


def test_register_rejects_invalid_username(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "fred@acme.com",
            "full_name": "Fred",
            "password": "strongpass1",
            "username": "1starts_with_digit",  # must start with a letter
        },
    )
    assert r.status_code == 422


def test_register_rejects_username_with_invalid_chars(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "gina@acme.com",
            "full_name": "Gina",
            "password": "strongpass1",
            "username": "has spaces",
        },
    )
    assert r.status_code == 422


def test_register_rejects_username_too_short(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "hank@acme.com",
            "full_name": "Hank",
            "password": "strongpass1",
            "username": "ab",  # < 3 chars
        },
    )
    assert r.status_code == 422


def test_register_disambiguates_derived_username_on_collision(client):
    # First user takes the natural slot.
    body1 = register(client, email="iris@acme.com")
    assert body1["user"]["username"] == "iris"
    # Second user with the same derived handle but a different email gets
    # a numeric suffix (iris2, iris3, ...).
    body2 = register(client, email="iris@other.com")
    assert body2["user"]["username"].startswith("iris")
    assert body2["user"]["username"] != "iris"


# ---------------------------------------------------------------------------
# Email / password validation
# ---------------------------------------------------------------------------


def test_register_rejects_duplicate_email(client):
    register(client, email="jane@acme.com")
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "JANE@acme.com",  # case-folded, must still collide
            "full_name": "Other Jane",
            "password": "anotherpass1",
        },
    )
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_register_rejects_duplicate_username(client):
    register(client, email="kara@acme.com", username="shared_handle")
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "leo@acme.com",
            "full_name": "Leo",
            "password": "strongpass1",
            "username": "shared_handle",
        },
    )
    assert r.status_code == 409
    assert "taken" in r.json()["detail"]


def test_register_rejects_short_password(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "mia@acme.com",
            "full_name": "Mia",
            "password": "short",  # < 8 chars
        },
    )
    assert r.status_code == 422


def test_register_rejects_oversize_password(client):
    # 73 chars of ASCII = 73 bytes > 72-byte bcrypt cap.
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ned@acme.com",
            "full_name": "Ned",
            "password": "a" * 73,
        },
    )
    assert r.status_code == 422


def test_register_rejects_invalid_email(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "full_name": "Bad",
            "password": "strongpass1",
        },
    )
    assert r.status_code == 422


def test_register_rejects_missing_full_name(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "opal@acme.com",
            "password": "strongpass1",
        },
    )
    assert r.status_code == 422


def test_register_rejects_extra_unknown_field(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "paul@acme.com",
            "full_name": "Paul",
            "password": "strongpass1",
            "is_admin": True,  # extra=forbid means this 422s
        },
    )
    assert r.status_code == 422


def test_register_password_with_multibyte_chars_under_cap(client):
    # 14 chars × 4 bytes = 56 bytes — under cap, must succeed.
    body = register(
        client,
        email="quinn@acme.com",
        password="密码密码密码密码密码密码密码a",  # 14 chars, 14*3+1 = 43 bytes
    )
    assert body["user"]["email"] == "quinn@acme.com"


def test_register_password_with_multibyte_chars_over_cap(client):
    # 25 Chinese chars × 3 bytes = 75 bytes > 72-byte cap; reject.
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "rita@acme.com",
            "full_name": "Rita",
            "password": "密" * 25,  # 75 bytes
        },
    )
    assert r.status_code == 422
