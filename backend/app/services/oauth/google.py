"""Google OAuth2 / OIDC integration.

The module is split into two layers so the FastAPI route can stay thin
and the test suite can swap in a fake:

* :func:`get_google_oauth_client` — Authlib ``OAuth`` registry pre-wired
  with Google's OIDC discovery document. The registry is lazily built
  once per process (Authlib caches the JWKS internally after the first
  call). Tests can override the function via FastAPI dependency
  injection.

* :class:`GoogleUserInfo` — a tiny dataclass that captures only the
  fields we care about (``sub``, ``email``, ``email_verified``, ``name``,
  ``picture``). Defining our own shape decouples the rest of the code
  from Authlib's claim dict and makes mocking trivial.

* :func:`extract_userinfo` — turns Authlib's ``token`` dict (returned by
  ``authorize_access_token``) into a :class:`GoogleUserInfo`. Tries the
  ``userinfo`` claim first (preferred — it's already validated by
  Authlib's OIDC pipeline), falls back to calling the userinfo endpoint
  if the id_token didn't carry the profile fields.

Why the indirection: Authlib's ``OAuth`` is heavily stateful (registers
a session under the hood, requires a Starlette ``Request``, talks to
remote endpoints during ``authorize_access_token``). Tests would need to
stand up a real OIDC discovery doc + token endpoint to exercise it. By
exposing the registry as a dependency-injectable factory we can replace
it with a fake that returns canned tokens, while keeping production
fully Authlib-driven.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

log = logging.getLogger("shadowblade.oauth.google")


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------


_oauth_singleton: OAuth | None = None


def _build_oauth_registry() -> OAuth:
    """Construct the Authlib ``OAuth`` registry with Google registered.

    ``server_metadata_url`` points at the OIDC discovery document — Authlib
    auto-discovers the authorize / token / userinfo endpoints and the JWKS
    URI from it. The first ``authorize_redirect`` call against the client
    triggers a one-shot HTTP GET for the document and caches it.
    """
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url=settings.google_oidc_metadata_url,
        client_kwargs={
            "scope": settings.google_oauth_scopes,
            # ``prompt=select_account`` makes Google always show the account
            # chooser, even if the user is already logged in to a single
            # Google account. Useful for shared computers; remove if you
            # want silent SSO.
            "prompt": "select_account",
        },
    )
    return oauth


def get_google_oauth_client() -> OAuth:
    """FastAPI dependency — return the lazily-built Authlib ``OAuth`` instance.

    Tests override this in ``app.dependency_overrides`` to swap in a
    fake that doesn't hit Google.
    """
    global _oauth_singleton
    if _oauth_singleton is None:
        _oauth_singleton = _build_oauth_registry()
    return _oauth_singleton


def reset_google_oauth_client() -> None:
    """Drop the cached registry — call from tests after settings change."""
    global _oauth_singleton
    _oauth_singleton = None


# ---------------------------------------------------------------------------
# Profile shape
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoogleUserInfo:
    """Subset of the Google userinfo / id_token claims we care about.

    Frozen so the routing layer treats it as a read-only value object.
    """

    sub: str  # stable user id assigned by Google; survives email changes
    email: str
    email_verified: bool
    name: str | None
    picture: str | None
    raw: dict[str, Any]  # full payload for audit + raw_profile storage


def extract_userinfo(token: dict[str, Any]) -> GoogleUserInfo:
    """Coerce Authlib's token dict into a :class:`GoogleUserInfo`.

    Authlib parses the id_token automatically when the client was
    registered with ``server_metadata_url`` pointing at an OIDC discovery
    doc. The parsed claims land in ``token["userinfo"]``.

    Raises
    ------
    ValueError
        If the token has no ``userinfo`` *and* no ``sub`` / ``email``
        directly — that means Google sent back something we can't act
        on. Routing turns this into a 400.
    """
    userinfo = token.get("userinfo") or {}
    # Some Authlib versions stash claims under a different key — fall
    # back to scanning the token itself.
    if not userinfo and "sub" in token:
        userinfo = {
            k: token.get(k)
            for k in ("sub", "email", "email_verified", "name", "picture")
        }

    sub = userinfo.get("sub")
    email = userinfo.get("email")
    if not sub or not email:
        raise ValueError(
            "google userinfo missing required 'sub' or 'email' claims"
        )

    return GoogleUserInfo(
        sub=str(sub),
        email=str(email).lower(),
        email_verified=bool(userinfo.get("email_verified", False)),
        name=userinfo.get("name"),
        picture=userinfo.get("picture"),
        raw=dict(userinfo),
    )


__all__ = [
    "GoogleUserInfo",
    "extract_userinfo",
    "get_google_oauth_client",
    "reset_google_oauth_client",
]
