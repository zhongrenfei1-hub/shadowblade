"""Callback flow when the user already exists — link vs re-login paths."""

from __future__ import annotations

import anyio
import pytest
from sqlalchemy import select

from app.core.security import OAUTH_ONLY_PASSWORD_HASH
from app.models import OAuthAccount, User
from tests.google_auth.conftest import make_token, make_userinfo


def _callback(client, fake_oauth, token_response):
    fake_oauth.google.token_response = token_response
    return client.get(
        "/api/v1/auth/google/callback?intent=json&code=fake-code",
        follow_redirects=False,
    )


def _register_password_user(client, *, email: str, password: str = "strongpass1") -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Existing User", "password": password},
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Email-based link
# ---------------------------------------------------------------------------


def test_callback_links_existing_password_user_by_email(client, fake_oauth):
    pw_body = _register_password_user(client, email="alice@example.com")

    r = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(email="alice@example.com")),
    )
    body = r.json()
    assert r.status_code == 200
    assert body["is_new_user"] is False
    # Same user id — Google was linked, not a new account.
    assert body["user"]["id"] == pw_body["user"]["id"]


def test_callback_link_preserves_password_login(client, fake_oauth, db_engine):
    _register_password_user(
        client, email="bob@example.com", password="strongpass1"
    )
    _callback(
        client, fake_oauth, make_token(make_userinfo(email="bob@example.com"))
    )
    # Password login still works after Google link.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "strongpass1"},
    )
    assert r.status_code == 200


def test_callback_link_creates_oauth_row(client, fake_oauth, db_engine):
    _register_password_user(client, email="carol@example.com")
    _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(sub="link-sub-1", email="carol@example.com")),
    )
    _, factory = db_engine

    async def _inspect():
        async with factory() as s:
            row = (
                await s.execute(
                    select(OAuthAccount).where(
                        OAuthAccount.provider == "google",
                        OAuthAccount.provider_user_id == "link-sub-1",
                    )
                )
            ).scalars().first()
            assert row is not None
            assert row.email == "carol@example.com"

    anyio.run(_inspect)


def test_callback_link_email_is_case_insensitive(client, fake_oauth):
    """Existing email 'Dora@x.com' matches Google's 'DORA@x.com'."""
    pw_body = _register_password_user(client, email="Dora@example.com")

    r = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(email="DORA@EXAMPLE.COM")),
    )
    body = r.json()
    assert body["user"]["id"] == pw_body["user"]["id"]


def test_callback_link_promotes_email_verification(client, fake_oauth, db_engine):
    """Unverified password user becomes verified when Google confirms email."""
    pw_body = _register_password_user(client, email="ed@example.com")
    assert pw_body["user"]["is_verified"] is False

    r = _callback(
        client,
        fake_oauth,
        make_token(
            make_userinfo(email="ed@example.com", email_verified=True)
        ),
    )
    body = r.json()
    assert body["user"]["is_verified"] is True
    assert body["user"]["email_verified_at"] is not None


def test_callback_link_skips_verification_when_google_unsure(
    client, fake_oauth
):
    pw_body = _register_password_user(client, email="fred@example.com")
    assert pw_body["user"]["is_verified"] is False

    r = _callback(
        client,
        fake_oauth,
        make_token(
            make_userinfo(email="fred@example.com", email_verified=False)
        ),
    )
    body = r.json()
    assert body["user"]["is_verified"] is False


# ---------------------------------------------------------------------------
# OAuth-row-based re-login (subsequent visits)
# ---------------------------------------------------------------------------


def test_callback_returns_existing_user_on_second_visit(client, fake_oauth):
    first = _callback(client, fake_oauth, make_token(make_userinfo(sub="sub-1")))
    second = _callback(client, fake_oauth, make_token(make_userinfo(sub="sub-1")))
    assert first.json()["user"]["id"] == second.json()["user"]["id"]
    assert first.json()["is_new_user"] is True
    assert second.json()["is_new_user"] is False


def test_callback_refreshes_profile_snapshot_on_relogin(
    client, fake_oauth, db_engine
):
    """Profile changes on Google's side update the OAuthAccount row."""
    _callback(
        client,
        fake_oauth,
        make_token(
            make_userinfo(sub="sub-x", name="Old Name", picture="https://old.png")
        ),
    )
    _callback(
        client,
        fake_oauth,
        make_token(
            make_userinfo(sub="sub-x", name="New Name", picture="https://new.png")
        ),
    )
    _, factory = db_engine

    async def _inspect():
        async with factory() as s:
            row = (
                await s.execute(
                    select(OAuthAccount).where(
                        OAuthAccount.provider == "google",
                        OAuthAccount.provider_user_id == "sub-x",
                    )
                )
            ).scalars().first()
            assert row.name == "New Name"
            assert row.avatar_url == "https://new.png"

    anyio.run(_inspect)


def test_callback_bumps_last_login_at_on_relogin(client, fake_oauth, db_engine):
    body1 = _callback(
        client, fake_oauth, make_token(make_userinfo(sub="sub-l1"))
    ).json()
    first_ts = body1["user"]["last_login_at"]
    body2 = _callback(
        client, fake_oauth, make_token(make_userinfo(sub="sub-l1"))
    ).json()
    second_ts = body2["user"]["last_login_at"]
    assert second_ts >= first_ts


def test_callback_for_oauth_sub_overrides_email_match(client, fake_oauth):
    """If a user already linked Google as ``sub=A``, a second password
    user with the same email never wins — the sub-keyed row is the
    source of truth."""
    google_body = _callback(
        client,
        fake_oauth,
        make_token(
            make_userinfo(sub="sub-1", email="overlap@example.com")
        ),
    ).json()
    # Now another user registers via password with the same email —
    # this is actually a conflict because email is unique. So we'd
    # expect 409. That's the "register can't take an email already
    # owned by a Google login" check.
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "overlap@example.com",
            "full_name": "Overlap",
            "password": "strongpass1",
        },
    )
    assert r.status_code == 409
    # And re-login via Google still hits the original user.
    again = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(sub="sub-1", email="overlap@example.com")),
    ).json()
    assert again["user"]["id"] == google_body["user"]["id"]
