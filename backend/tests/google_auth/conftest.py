"""Test fixtures for the Google OAuth integration.

The whole point of the fakes here is to drive ``/auth/google/login`` and
``/auth/google/callback`` without touching the real Google endpoints.

Two mocks are wired:

* :class:`FakeGoogleOAuth` stands in for the Authlib ``OAuth`` registry
  returned by :func:`app.services.oauth.google.get_google_oauth_client`.
  It exposes a ``google`` attribute with the two methods the route
  layer calls — ``authorize_redirect`` and ``authorize_access_token`` —
  and lets each test seed the response.

* ``configure_google_settings`` fixture writes test values to
  ``settings.google_client_id`` / ``_secret`` / ``_redirect_uri`` so the
  ``_ensure_google_configured`` guard doesn't 503.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient

# Re-export the org-level fixtures (client + db_engine) so the Google
# auth tests share the same per-test SQLite scaffolding.
from tests.organizations.conftest import (  # noqa: F401
    _reset_settings_cache,
    db_engine,
)


# ---------------------------------------------------------------------------
# FakeGoogleOAuth — the bare minimum to satisfy the route handlers
# ---------------------------------------------------------------------------


class _FakeGoogleClient:
    """Stand-in for ``OAuth().google`` from Authlib.

    Tests assign ``token_response`` (and/or ``token_error``) before
    hitting the callback endpoint to control what the fake returns.
    """

    def __init__(self) -> None:
        self.token_response: dict[str, Any] | None = None
        self.token_error: Exception | None = None
        # Inspectable: assigned by ``authorize_redirect`` so tests can
        # assert on the URL/state the route picked.
        self.last_redirect_url: str | None = None

    async def authorize_redirect(self, request, redirect_uri: str):
        # Generate a fake-but-realistic state token and write it to the
        # session so callback's ``request.session.pop(...)`` can find it
        # if we ever exercise Authlib's full state-check (we don't —
        # Authlib's real check is skipped here because the fake replaces
        # the entire client).
        import secrets

        state = secrets.token_urlsafe(16)
        request.session["_state_google_" + state] = {
            "data": {"redirect_uri": redirect_uri},
        }
        url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            + urlencode({"state": state, "redirect_uri": redirect_uri})
        )
        self.last_redirect_url = url
        return RedirectResponse(url, status_code=302)

    async def authorize_access_token(self, request):
        if self.token_error is not None:
            raise self.token_error
        if self.token_response is None:
            raise AssertionError(
                "FakeGoogleClient.token_response was not configured for this test"
            )
        return self.token_response


class FakeGoogleOAuth:
    """Stand-in for the Authlib ``OAuth`` registry."""

    def __init__(self) -> None:
        self.google = _FakeGoogleClient()


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def configure_google_settings(monkeypatch):
    """Populate the Google settings so ``_ensure_google_configured`` passes."""
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(
        cfg.settings, "google_client_secret", "test-client-secret"
    )
    monkeypatch.setattr(
        cfg.settings,
        "google_redirect_uri",
        "http://testserver/api/v1/auth/google/callback",
    )
    monkeypatch.setattr(
        cfg.settings,
        "google_post_login_redirect",
        "http://localhost:3000/auth/callback",
    )
    monkeypatch.setattr(cfg.settings, "environment", "test")
    yield


@pytest.fixture
def fake_oauth() -> FakeGoogleOAuth:
    return FakeGoogleOAuth()


@pytest_asyncio.fixture
async def client(db_engine, fake_oauth, configure_google_settings):
    """TestClient wired to the per-test DB *and* the FakeGoogleOAuth.

    Overrides:
    * ``get_db`` → per-test SQLite session.
    * ``get_google_oauth_client`` → the FakeGoogleOAuth instance.
    """
    engine, session_factory = db_engine

    from app.api.deps import get_db
    from app.main import app
    from app.services.oauth.google import get_google_oauth_client

    async def _get_db_override():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_google_oauth_client] = lambda: fake_oauth

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_google_oauth_client, None)


# ---------------------------------------------------------------------------
# Test-data helpers
# ---------------------------------------------------------------------------


def make_userinfo(
    *,
    sub: str = "1234567890",
    email: str = "alice@example.com",
    email_verified: bool = True,
    name: str | None = "Alice Example",
    picture: str | None = "https://lh3.googleusercontent.com/a/alice.jpg",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Google ``userinfo`` claim dict for the fake to return."""
    body = {
        "sub": sub,
        "email": email,
        "email_verified": email_verified,
        "name": name,
        "picture": picture,
    }
    if extra:
        body.update(extra)
    return body


def make_token(userinfo: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the dict that Authlib's ``authorize_access_token`` returns.

    Authlib stashes the parsed id_token claims under ``userinfo``, which
    is the shape our ``extract_userinfo`` expects.
    """
    if userinfo is None:
        userinfo = make_userinfo()
    return {
        "access_token": "fake-access-token",
        "id_token": "fake.id.token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "userinfo": userinfo,
    }


__all__ = [
    "FakeGoogleOAuth",
    "client",
    "configure_google_settings",
    "db_engine",
    "fake_oauth",
    "make_token",
    "make_userinfo",
]
