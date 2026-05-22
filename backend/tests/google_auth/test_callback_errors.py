"""Error-path tests for ``/auth/google/callback``.

Covers:
* Google reported an explicit error (user clicked Cancel)
* Authlib failed to exchange the code
* Token payload was missing required claims
* Disabled local accounts refuse to log in
* Missing config → 503
"""

from __future__ import annotations

import anyio
import pytest
from sqlalchemy import update

from app.models import User
from tests.google_auth.conftest import make_token, make_userinfo


def _callback(client, fake_oauth, token_response=None, *, query=""):
    if token_response is not None:
        fake_oauth.google.token_response = token_response
    return client.get(
        f"/api/v1/auth/google/callback?intent=json&code=fake-code{query}",
        follow_redirects=False,
    )


def test_callback_returns_400_when_google_reports_error(client, fake_oauth):
    r = client.get(
        "/api/v1/auth/google/callback?intent=json&error=access_denied",
        follow_redirects=False,
    )
    assert r.status_code == 400
    assert "denied authorisation" in r.json()["detail"]


def test_callback_returns_401_on_authlib_error(client, fake_oauth):
    from authlib.integrations.base_client.errors import OAuthError

    fake_oauth.google.token_error = OAuthError(description="state mismatch")
    r = _callback(client, fake_oauth)
    assert r.status_code == 401
    assert "handshake failed" in r.json()["detail"]


def test_callback_returns_400_when_userinfo_missing_sub(client, fake_oauth):
    # Drop the sub claim — extract_userinfo raises ValueError, route 400s.
    bad = {
        "access_token": "x",
        "userinfo": {"email": "nosub@example.com"},
    }
    r = _callback(client, fake_oauth, bad)
    assert r.status_code == 400
    assert "missing required" in r.json()["detail"]


def test_callback_returns_400_when_userinfo_missing_email(client, fake_oauth):
    bad = {
        "access_token": "x",
        "userinfo": {"sub": "no-email-sub"},
    }
    r = _callback(client, fake_oauth, bad)
    assert r.status_code == 400


def test_callback_returns_400_when_no_userinfo_at_all(client, fake_oauth):
    # Token contains neither userinfo nor inline claims.
    bad = {"access_token": "x", "id_token": "y"}
    r = _callback(client, fake_oauth, bad)
    assert r.status_code == 400


def test_callback_falls_back_to_inline_claims_without_userinfo_key(
    client, fake_oauth
):
    """Older Authlib versions stash claims at top level instead of nested."""
    inline = {
        "access_token": "x",
        "id_token": "y",
        "sub": "inline-sub",
        "email": "inline@example.com",
        "email_verified": True,
        "name": "Inline",
        "picture": None,
    }
    r = _callback(client, fake_oauth, inline)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "inline@example.com"


def test_callback_returns_403_when_local_account_disabled(
    client, fake_oauth, db_engine
):
    # Pre-create a disabled user via password registration + disable.
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "disabled@example.com",
            "full_name": "Disabled",
            "password": "strongpass1",
        },
    ).json()
    _, factory = db_engine

    async def _disable():
        async with factory() as s:
            await s.execute(
                update(User)
                .where(User.id == reg["user"]["id"])
                .values(is_active=False)
            )
            await s.commit()

    anyio.run(_disable)

    r = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(email="disabled@example.com")),
    )
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"]


def test_callback_returns_403_when_oauth_linked_account_disabled(
    client, fake_oauth, db_engine
):
    """Same disable check fires on the OAuth-row reuse path."""
    body = _callback(
        client, fake_oauth, make_token(make_userinfo(sub="dsbl-sub"))
    ).json()
    _, factory = db_engine

    async def _disable():
        async with factory() as s:
            await s.execute(
                update(User)
                .where(User.id == body["user"]["id"])
                .values(is_active=False)
            )
            await s.commit()

    anyio.run(_disable)

    r = _callback(
        client, fake_oauth, make_token(make_userinfo(sub="dsbl-sub"))
    )
    assert r.status_code == 403


def test_callback_returns_503_when_unconfigured(client, monkeypatch, fake_oauth):
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "google_client_id", "")
    r = _callback(client, fake_oauth, make_token())
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Password-change flow rejects OAuth-only accounts
# ---------------------------------------------------------------------------


def test_password_change_refuses_oauth_only_account(client, fake_oauth):
    body = _callback(client, fake_oauth, make_token()).json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    r = client.post(
        "/api/v1/auth/password/change",
        json={"current_password": "anything", "new_password": "newpassword1"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "social provider" in r.json()["detail"]


def test_password_login_refuses_oauth_only_account(client, fake_oauth):
    _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(email="oauth-only@example.com")),
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "oauth-only@example.com", "password": "anyguess1"},
    )
    # Should NOT log in — sentinel hash won't match anything.
    assert r.status_code == 401
