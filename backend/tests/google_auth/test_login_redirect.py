"""``GET /auth/google/login`` — kicks off the OAuth dance.

Covers:
* happy-path 302 to Google
* missing config → 503
* ``next`` allow-listing (captured to session)
* Authlib OAuthError → 502
"""

from __future__ import annotations

import pytest


def test_login_redirects_to_google(client, fake_oauth):
    r = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    # The route delegated to our fake — confirm it captured the URL.
    assert fake_oauth.google.last_redirect_url == loc


def test_login_includes_redirect_uri_in_authorize_url(client, fake_oauth):
    r = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert r.status_code == 302
    # The redirect URI passed to Google matches the configured one.
    assert (
        "redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback"
        in r.headers["location"]
    )


def test_login_returns_503_when_unconfigured(client, monkeypatch):
    # Wipe the client_id — _ensure_google_configured should bail.
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "google_client_id", "")
    r = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"]


def test_login_returns_503_when_secret_missing(client, monkeypatch):
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "google_client_secret", "")
    r = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert r.status_code == 503


def test_login_captures_next_query_into_session(client):
    # Use the same TestClient instance to retain the session cookie.
    r = client.get(
        "/api/v1/auth/google/login?next=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fcallback%3Fdest%3Dapp",
        follow_redirects=False,
    )
    assert r.status_code == 302
    # Session cookie set → middleware stored ``next`` for the callback.
    assert "session" in r.headers.get("set-cookie", "")


def test_login_authlib_error_returns_502(client, fake_oauth):
    from authlib.integrations.base_client.errors import OAuthError

    async def boom(*_args, **_kwargs):
        raise OAuthError(description="fake authorize failure")

    fake_oauth.google.authorize_redirect = boom  # type: ignore[assignment]
    r = client.get("/api/v1/auth/google/login", follow_redirects=False)
    assert r.status_code == 502
    assert "google oauth error" in r.json()["detail"]


def test_login_with_explicit_redirect_intent_still_redirects(client):
    # ``intent`` is a callback-only knob; on /login it should be ignored.
    r = client.get(
        "/api/v1/auth/google/login?intent=json",
        follow_redirects=False,
    )
    assert r.status_code == 302
