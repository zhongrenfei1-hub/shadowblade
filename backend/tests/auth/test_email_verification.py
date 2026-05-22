"""Email-verification endpoint tests.

* ``POST /auth/email/verify``               — token consumption
* ``POST /auth/email/resend-verification``  — authed, re-issues a token
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.core.config import settings
from app.core.security import (
    EMAIL_VERIFY_TOKEN_TYPE,
    generate_email_verification_token,
)
from tests.auth._helpers import auth_headers, register


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def test_verify_marks_user_verified(client):
    body = register(client, email="alice@acme.com")
    token = body["email_verification_token"]
    r = client.post(
        "/api/v1/auth/email/verify",
        json={"token": token},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # /me reflects the new state.
    headers = auth_headers(body["access_token"])
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["user"]["is_verified"] is True
    assert me["user"]["email_verified_at"] is not None


def test_verify_is_idempotent(client):
    body = register(client, email="bob@acme.com")
    token = body["email_verification_token"]
    # First call: verifies.
    r1 = client.post("/api/v1/auth/email/verify", json={"token": token})
    assert r1.status_code == 200
    # Second call with the same token: also returns 200 with a different
    # message — frontend can refresh the page without seeing an error.
    r2 = client.post("/api/v1/auth/email/verify", json={"token": token})
    assert r2.status_code == 200
    assert "already" in r2.json()["message"]


def test_verify_rejects_invalid_token(client):
    r = client.post(
        "/api/v1/auth/email/verify",
        json={"token": "not.a.valid.jwt"},
    )
    assert r.status_code == 401


def test_verify_rejects_access_token(client):
    body = register(client, email="carol@acme.com")
    r = client.post(
        "/api/v1/auth/email/verify",
        json={"token": body["access_token"]},
    )
    assert r.status_code == 401


def test_verify_rejects_expired_token(client):
    register(client, email="diana@acme.com")
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": "diana@acme.com",
            "iat": int((now - timedelta(days=3)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "type": EMAIL_VERIFY_TOKEN_TYPE,
            "jti": "expired-verify",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = client.post(
        "/api/v1/auth/email/verify",
        json={"token": expired},
    )
    assert r.status_code == 401


def test_verify_for_unknown_user_returns_404(client):
    # Token is structurally valid but no user matches.
    forged = generate_email_verification_token("phantom@nowhere.com")
    r = client.post(
        "/api/v1/auth/email/verify",
        json={"token": forged},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Resend
# ---------------------------------------------------------------------------


def test_resend_requires_authentication(client):
    r = client.post("/api/v1/auth/email/resend-verification")
    assert r.status_code == 401


def test_resend_returns_a_fresh_token(client):
    body = register(client, email="ed@acme.com")
    headers = auth_headers(body["access_token"])
    r = client.post("/api/v1/auth/email/resend-verification", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["verification_token"]
    # Different from the one returned on register (different jti).
    assert data["verification_token"] != body["email_verification_token"]


def test_resend_returns_no_token_when_already_verified(client):
    body = register(client, email="fred@acme.com")
    headers = auth_headers(body["access_token"])
    # First, verify.
    client.post(
        "/api/v1/auth/email/verify",
        json={"token": body["email_verification_token"]},
    )
    # Now resend should short-circuit.
    r = client.post(
        "/api/v1/auth/email/resend-verification", headers=headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["verification_token"] is None
    assert "already" in data["message"]


def test_resend_token_is_actually_usable(client):
    body = register(client, email="gina@acme.com")
    headers = auth_headers(body["access_token"])
    rsd = client.post(
        "/api/v1/auth/email/resend-verification", headers=headers
    ).json()
    r = client.post(
        "/api/v1/auth/email/verify",
        json={"token": rsd["verification_token"]},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
