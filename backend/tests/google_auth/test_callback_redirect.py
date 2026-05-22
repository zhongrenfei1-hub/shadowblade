"""``/auth/google/callback`` without ``intent=json`` — redirect to frontend."""

from __future__ import annotations

import pytest
from urllib.parse import urlparse, parse_qs

from tests.google_auth.conftest import make_token, make_userinfo


def _callback_redirect(client, fake_oauth, *, next_url: str | None = None):
    fake_oauth.google.token_response = make_token()
    extra = f"&next={next_url}" if next_url else ""
    return client.get(
        f"/api/v1/auth/google/callback?code=fake{extra}",
        follow_redirects=False,
    )


def _parse_fragment(url: str) -> dict[str, str]:
    """Extract the URL fragment payload after ``#``."""
    parts = urlparse(url)
    if not parts.fragment:
        # When build_fragment_redirect appended ``#`` it may have used
        # the location string before urlparse picks it up — fall back to
        # manual split.
        if "#" in url:
            return dict(
                (k, v[0]) for k, v in parse_qs(url.split("#", 1)[1]).items()
            )
    return dict((k, v[0]) for k, v in parse_qs(parts.fragment).items())


def test_callback_redirects_to_default_frontend(client, fake_oauth):
    r = _callback_redirect(client, fake_oauth)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("http://localhost:3000/auth/callback")
    frag = _parse_fragment(loc)
    assert frag["access_token"]
    assert frag["refresh_token"]
    assert frag["token_type"] == "bearer"
    assert frag["is_new_user"] == "1"  # first sighting → new user
    assert frag["provider"] == "google"


def test_callback_redirect_tokens_are_usable(client, fake_oauth):
    r = _callback_redirect(client, fake_oauth)
    loc = r.headers["location"]
    frag = _parse_fragment(loc)
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {frag['access_token']}"},
    )
    assert me.status_code == 200


def test_callback_respects_safe_next_query(client, fake_oauth):
    """A ``next`` URL on the SAME origin as the default redirect is honoured."""
    # Drive login first so the session captures the ``next``.
    client.get(
        "/api/v1/auth/google/login?next=http%3A%2F%2Flocalhost%3A3000%2Fteam",
        follow_redirects=False,
    )
    fake_oauth.google.token_response = make_token()
    r = client.get(
        "/api/v1/auth/google/callback?code=fake",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers["location"].startswith("http://localhost:3000/team")


def test_callback_rejects_cross_origin_next(client, fake_oauth):
    """A ``next=https://evil.com/...`` is ignored — fall back to default."""
    client.get(
        "/api/v1/auth/google/login?next=https%3A%2F%2Fevil.com%2Fphish",
        follow_redirects=False,
    )
    fake_oauth.google.token_response = make_token()
    r = client.get(
        "/api/v1/auth/google/callback?code=fake",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers["location"].startswith("http://localhost:3000/auth/callback")


def test_callback_existing_user_returns_is_new_zero_in_fragment(client, fake_oauth):
    # First login creates the user.
    _callback_redirect(client, fake_oauth)
    # Second login returns the existing user with is_new_user=0.
    r = _callback_redirect(client, fake_oauth)
    frag = _parse_fragment(r.headers["location"])
    assert frag["is_new_user"] == "0"


def test_callback_default_intent_is_redirect(client, fake_oauth):
    """No ``intent`` query → 302 redirect (not JSON)."""
    fake_oauth.google.token_response = make_token()
    r = client.get(
        "/api/v1/auth/google/callback?code=fake",
        follow_redirects=False,
    )
    assert r.status_code == 302
    # The response body is empty for a RedirectResponse.
    assert r.headers["content-type"].startswith("text/") or not r.text


def test_callback_intent_json_returns_body_not_redirect(client, fake_oauth):
    fake_oauth.google.token_response = make_token()
    r = client.get(
        "/api/v1/auth/google/callback?intent=json&code=fake",
        follow_redirects=False,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    # No Location header on JSON intent.
    assert "location" not in {k.lower() for k in r.headers}
