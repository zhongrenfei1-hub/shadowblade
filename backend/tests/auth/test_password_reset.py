"""Password-recovery + password-reset endpoint tests.

Covers:

* ``POST /auth/password/recover``  — anti-enumeration + dev token surface
* ``POST /auth/password/reset``    — token consumption + new-password rules
* Token-type safety (refresh / access tokens rejected for reset)
* End-to-end: recover → reset → login with new password
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings
from app.core.security import (
    PASSWORD_RESET_TOKEN_TYPE,
    generate_password_reset_token,
    verify_password_reset_token,
)
from tests.auth._helpers import login, register


# ---------------------------------------------------------------------------
# Recover
# ---------------------------------------------------------------------------


def test_recover_returns_ok_and_dev_token_for_known_email(client):
    register(client, email="alice@acme.com")
    r = client.post(
        "/api/v1/auth/password/recover",
        json={"email": "alice@acme.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["reset_token"]  # exposed in dev mode
    # The token decodes back to the original email.
    email = verify_password_reset_token(body["reset_token"])
    assert email == "alice@acme.com"


def test_recover_returns_ok_for_unknown_email_no_token(client):
    # Anti-enumeration: ok=True even when the email is unknown, but no
    # reset_token is leaked.
    r = client.post(
        "/api/v1/auth/password/recover",
        json={"email": "ghost@acme.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["reset_token"] is None


def test_recover_is_case_insensitive_on_email(client):
    register(client, email="bob@acme.com")
    r = client.post(
        "/api/v1/auth/password/recover",
        json={"email": "BOB@ACME.COM"},
    )
    assert r.status_code == 200
    assert r.json()["reset_token"]


def test_recover_rejects_invalid_email(client):
    r = client.post(
        "/api/v1/auth/password/recover",
        json={"email": "not-an-email"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_changes_password_and_old_pw_stops_working(client):
    register(client, email="carol@acme.com", password="oldpassword1")
    # Get a token via the recover endpoint (dev mode surfaces it).
    rec = client.post(
        "/api/v1/auth/password/recover", json={"email": "carol@acme.com"}
    ).json()
    token = rec["reset_token"]
    # Use it to set a new password.
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": "freshpass1"},
    )
    assert r.status_code == 200

    # Old password no longer logs in.
    r1 = client.post(
        "/api/v1/auth/login",
        json={"email": "carol@acme.com", "password": "oldpassword1"},
    )
    assert r1.status_code == 401

    # New password logs in.
    fresh = login(
        client, email_or_username="carol@acme.com", password="freshpass1"
    )
    assert fresh["user"]["email"] == "carol@acme.com"


def test_reset_rejects_garbage_token(client):
    register(client, email="diana@acme.com")
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": "not.a.valid.jwt", "new_password": "newpassword1"},
    )
    assert r.status_code == 401


def test_reset_rejects_access_token_as_reset(client):
    body = register(client, email="ed@acme.com")
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": body["access_token"], "new_password": "newpassword1"},
    )
    assert r.status_code == 401


def test_reset_rejects_refresh_token_as_reset(client):
    body = register(client, email="fred@acme.com")
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": body["refresh_token"], "new_password": "newpassword1"},
    )
    assert r.status_code == 401


def test_reset_rejects_expired_token(client):
    register(client, email="gina@acme.com")
    # Build an already-expired reset token by hand.
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": "gina@acme.com",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "type": PASSWORD_RESET_TOKEN_TYPE,
            "jti": "expired-reset",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": expired, "new_password": "newpassword1"},
    )
    assert r.status_code == 401


def test_reset_for_unknown_user_returns_404(client):
    # Sign a valid token for an email that doesn't exist in the DB.
    forged = generate_password_reset_token("phantom@nowhere.com")
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": forged, "new_password": "newpassword1"},
    )
    assert r.status_code == 404


def test_reset_rejects_no_op_same_password(client):
    register(client, email="hank@acme.com", password="samepass1")
    rec = client.post(
        "/api/v1/auth/password/recover", json={"email": "hank@acme.com"}
    ).json()
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": rec["reset_token"], "new_password": "samepass1"},
    )
    assert r.status_code == 400
    assert "differ" in r.json()["detail"]


def test_reset_rejects_short_new_password(client):
    register(client, email="iris@acme.com")
    rec = client.post(
        "/api/v1/auth/password/recover", json={"email": "iris@acme.com"}
    ).json()
    r = client.post(
        "/api/v1/auth/password/reset",
        json={"token": rec["reset_token"], "new_password": "short"},
    )
    assert r.status_code == 422


def test_recover_then_reset_then_refresh_still_works(client):
    """End-to-end: recover → reset → login → refresh produces a usable pair."""
    register(client, email="jane@acme.com", password="oldpassword1")
    rec = client.post(
        "/api/v1/auth/password/recover", json={"email": "jane@acme.com"}
    ).json()
    client.post(
        "/api/v1/auth/password/reset",
        json={"token": rec["reset_token"], "new_password": "brandnewpass1"},
    )
    body = login(
        client, email_or_username="jane@acme.com", password="brandnewpass1"
    )
    # Refresh the freshly-issued pair.
    r = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert r.status_code == 200
