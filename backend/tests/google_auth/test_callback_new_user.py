"""``GET /auth/google/callback?intent=json`` — new-user creation path.

Verifies that the first time a Google sub shows up:
* a User row is created with email + name + picture from Google
* a personal workspace is bootstrapped (owner role)
* an OAuthAccount row is written with provider=google
* the response carries a valid JWT pair
* ``is_new_user`` is True
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.core.security import OAUTH_ONLY_PASSWORD_HASH, decode_access_token
from app.models import OAuthAccount, User, Workspace, WorkspaceMember
from tests.google_auth.conftest import make_token, make_userinfo


def _callback(client, fake_oauth, token_response):
    fake_oauth.google.token_response = token_response
    return client.get(
        "/api/v1/auth/google/callback?intent=json&code=fake-code",
        follow_redirects=False,
    )


def test_callback_creates_new_user(client, fake_oauth):
    r = _callback(client, fake_oauth, make_token())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_new_user"] is True
    assert body["provider"] == "google"
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["full_name"] == "Alice Example"
    assert body["user"]["avatar_url"] == "https://lh3.googleusercontent.com/a/alice.jpg"
    assert body["user"]["is_active"] is True
    # Google says email is verified → we trust it.
    assert body["user"]["is_verified"] is True
    assert body["user"]["email_verified_at"] is not None


def test_callback_token_pair_is_usable(client, fake_oauth):
    r = _callback(client, fake_oauth, make_token())
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    claims = decode_access_token(body["access_token"])
    assert int(claims["sub"]) == body["user"]["id"]
    # /me should work with the issued access token.
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "alice@example.com"


def test_callback_creates_personal_workspace(client, fake_oauth, db_engine):
    r = _callback(client, fake_oauth, make_token())
    body = r.json()
    assert body["default_workspace_id"] is not None
    assert any(o["role"] == "owner" for o in body["organizations"])

    # Inspect the DB directly to confirm the rows exist.
    import anyio

    _, factory = db_engine

    async def _inspect():
        async with factory() as s:
            ws = (
                await s.execute(
                    select(Workspace).where(Workspace.id == body["default_workspace_id"])
                )
            ).scalars().first()
            assert ws is not None
            assert ws.owner_id == body["user"]["id"]
            mem = (
                await s.execute(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == ws.id,
                        WorkspaceMember.user_id == body["user"]["id"],
                    )
                )
            ).scalars().first()
            assert mem is not None
            assert mem.role == "owner"

    anyio.run(_inspect)


def test_callback_writes_oauth_account_row(client, fake_oauth, db_engine):
    r = _callback(client, fake_oauth, make_token(make_userinfo(sub="abc-123")))
    body = r.json()
    import anyio

    _, factory = db_engine

    async def _inspect():
        async with factory() as s:
            row = (
                await s.execute(
                    select(OAuthAccount).where(
                        OAuthAccount.provider == "google",
                        OAuthAccount.provider_user_id == "abc-123",
                    )
                )
            ).scalars().first()
            assert row is not None
            assert row.user_id == body["user"]["id"]
            assert row.email == "alice@example.com"
            assert row.name == "Alice Example"
            # raw_profile is JSON-serialised — confirm round-trip.
            payload = json.loads(row.raw_profile)
            assert payload["sub"] == "abc-123"

    anyio.run(_inspect)


def test_callback_assigns_oauth_only_password_sentinel(
    client, fake_oauth, db_engine
):
    r = _callback(client, fake_oauth, make_token())
    body = r.json()
    import anyio

    _, factory = db_engine

    async def _inspect():
        async with factory() as s:
            user = await s.get(User, body["user"]["id"])
            assert user.hashed_password == OAUTH_ONLY_PASSWORD_HASH

    anyio.run(_inspect)


def test_callback_derives_username_from_email(client, fake_oauth):
    r = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(email="charlie.davis@example.com")),
    )
    body = r.json()
    assert body["user"]["username"] == "charlie.davis"


def test_callback_falls_back_to_email_prefix_when_name_missing(
    client, fake_oauth
):
    r = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(name=None, email="dan@example.com")),
    )
    body = r.json()
    # ``full_name`` falls back to the email's local part.
    assert body["user"]["full_name"] == "dan"


def test_callback_with_unverified_email_still_creates_user(client, fake_oauth):
    r = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(email_verified=False)),
    )
    body = r.json()
    assert r.status_code == 200
    # ...but the local user is NOT marked verified — we don't promise
    # verification on Google's behalf when Google itself isn't sure.
    assert body["user"]["is_verified"] is False
    assert body["user"]["email_verified_at"] is None


def test_callback_email_is_lowercased(client, fake_oauth):
    r = _callback(
        client,
        fake_oauth,
        make_token(make_userinfo(email="MIXED.case@Example.COM")),
    )
    body = r.json()
    assert body["user"]["email"] == "mixed.case@example.com"
