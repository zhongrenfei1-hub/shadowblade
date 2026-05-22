"""Google OAuth2 / OIDC login endpoints.

Two endpoints, both mounted under ``/api/v1/auth/google``:

* ``GET /login`` — kicks off the OAuth dance. Generates ``state`` + PKCE
  code verifier, stashes them in the signed session cookie (handled by
  ``SessionMiddleware``), and 302s to Google's authorize URL.

* ``GET /callback`` — Google's redirect target. Validates ``state``,
  exchanges the auth code for an id_token + access_token, extracts the
  user profile, upserts the local User + OAuthAccount rows, mints a JWT
  pair, and either:

    - returns it as JSON when ``intent=json`` is on the query string
      (used by tests and SPA callbacks that drive their own routing), or
    - 302s back to ``settings.google_post_login_redirect`` with the pair
      appended as a URL fragment (the default — works for any framework
      since fragments are kept off server logs and bounce purely
      browser-side).

Upsert resolution order (matches fastapi-fullstack-template):

1. ``(provider=google, provider_user_id=sub)`` hit → reuse that User.
2. Email hit (no OAuth row yet) → link Google to the existing account.
3. Neither hit → create a new User + a personal workspace and link
   Google as the first OAuthAccount.

In step 2 we never trust Google's ``email_verified`` claim to override
a *disabled* local account — disabled means the operator has revoked
access and that supersedes the SSO grant.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Annotated, Any
from urllib.parse import urlencode

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import (
    OAUTH_ONLY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
)
from app.models import OAuthAccount, User, Workspace, WorkspaceMember
from app.schemas.auth import GoogleCallbackResponse
from app.schemas.organization import OrganizationSummary
from app.schemas.user import UserRead, validate_username
from app.services.oauth.google import (
    GoogleUserInfo,
    extract_userinfo,
    get_google_oauth_client,
)

log = logging.getLogger("shadowblade.api.google_auth")
router = APIRouter(prefix="/auth/google", tags=["auth"])

GOOGLE_PROVIDER = "google"


# ---------------------------------------------------------------------------
# Helpers (mostly shared shape with app.api.auth)
# ---------------------------------------------------------------------------


_SLUG_FALLBACK_RE = re.compile(r"[^a-z0-9]+")
_USERNAME_FALLBACK_RE = re.compile(r"[^a-z0-9_.]+")


def _slug_from_email(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    base = _SLUG_FALLBACK_RE.sub("-", local).strip("-")
    if not base:
        base = "team"
    if len(base) < 2:
        base = base + "x"
    return base[:32]


def _username_from_email(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    cleaned = _USERNAME_FALLBACK_RE.sub("", local).strip("._")
    if not cleaned or not cleaned[0].isalpha():
        cleaned = "user" + (cleaned or "")
    return cleaned[:48]


async def _allocate_unique_username(db: AsyncSession, base: str) -> str:
    candidate = base
    attempt = 0
    while True:
        existing = (
            await db.execute(select(User.id).where(User.username == candidate))
        ).first()
        if existing is None:
            return candidate
        attempt += 1
        if attempt > 50:
            raise HTTPException(
                status_code=500,
                detail="could not allocate a unique username",
            )
        candidate = f"{base}{attempt}"[:48]


async def _allocate_unique_slug(db: AsyncSession, base: str) -> str:
    candidate = base
    attempt = 0
    while True:
        existing = (
            await db.execute(select(Workspace.id).where(Workspace.slug == candidate))
        ).first()
        if existing is None:
            return candidate
        attempt += 1
        if attempt > 50:
            raise HTTPException(
                status_code=500,
                detail="could not allocate a unique workspace slug",
            )
        candidate = f"{base}-{attempt}"


def _token_envelope(user: User, default_ws: int | None) -> dict:
    extra_claims = {"ws": default_ws} if default_ws else None
    access = create_access_token(user.id, extra_claims=extra_claims)
    refresh = create_refresh_token(user.id)
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": settings.jwt_ttl_minutes * 60,
        "refresh_token": refresh,
        "refresh_expires_in": settings.jwt_refresh_ttl_minutes * 60,
    }


async def _summarise_user_orgs(
    db: AsyncSession, user_id: int
) -> list[OrganizationSummary]:
    stmt = (
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        OrganizationSummary(
            id=ws.id,
            slug=ws.slug,
            name=ws.name,
            avatar_url=ws.avatar_url,
            role=role,
        )
        for ws, role in rows
    ]


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------


async def _find_user_by_oauth(
    db: AsyncSession, *, provider: str, provider_user_id: str
) -> tuple[User, OAuthAccount] | None:
    """Return ``(user, account)`` for the matching OAuthAccount, or None."""
    row = (
        await db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
    ).scalars().first()
    if row is None:
        return None
    user = await db.get(User, row.user_id)
    if user is None:
        # Orphaned OAuth row — should never happen given the ON DELETE
        # CASCADE, but treat as "no link" rather than crashing.
        log.warning(
            "orphaned OAuthAccount id=%s pointing at missing user_id=%s",
            row.id,
            row.user_id,
        )
        return None
    return user, row


async def _find_user_by_email(db: AsyncSession, email: str) -> User | None:
    return (
        await db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
    ).scalars().first()


async def _create_user_and_workspace(
    db: AsyncSession, info: GoogleUserInfo
) -> User:
    """Create a brand-new User + personal Workspace + WorkspaceMember.

    Used when the Google callback fires for an email we've never seen.
    Mirrors the bootstrap that ``POST /auth/register`` runs so
    Google-onboarded users are indistinguishable from password
    onboarded ones from the org-management surface's perspective.
    """
    base_username = _username_from_email(info.email)
    try:
        base_username = validate_username(base_username)
    except ValueError:
        base_username = "user"
    username = await _allocate_unique_username(db, base_username)

    user = User(
        email=info.email,
        username=username,
        full_name=info.name or info.email.split("@", 1)[0],
        avatar_url=info.picture,
        # Sentinel: this account has no password. The login / password
        # change endpoints recognise it and refuse with a 401/400.
        hashed_password=OAUTH_ONLY_PASSWORD_HASH,
        is_active=True,
        # Trust Google's verification — if Google says the email is
        # verified, we don't make the user click another link.
        is_verified=info.email_verified,
        email_verified_at=(
            datetime.now(timezone.utc) if info.email_verified else None
        ),
    )
    db.add(user)
    await db.flush()

    base_slug = _slug_from_email(info.email)
    slug = await _allocate_unique_slug(db, base_slug)
    ws = Workspace(
        slug=slug,
        name=f"{user.full_name} 的团队",
        owner_id=user.id,
        plan="starter",
        seats=5,
        monthly_render_quota=50,
    )
    db.add(ws)
    await db.flush()

    membership = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="owner",
        invited_by=None,
    )
    db.add(membership)
    await db.flush()
    return user


def _build_oauth_row(
    *, user_id: int, info: GoogleUserInfo, now: datetime
) -> OAuthAccount:
    return OAuthAccount(
        user_id=user_id,
        provider=GOOGLE_PROVIDER,
        provider_user_id=info.sub,
        email=info.email,
        name=info.name,
        avatar_url=info.picture,
        raw_profile=json.dumps(info.raw, default=str),
        last_login_at=now,
    )


def _refresh_oauth_row(row: OAuthAccount, info: GoogleUserInfo, now: datetime) -> None:
    """Update an existing OAuthAccount with the latest profile snapshot."""
    row.email = info.email
    row.name = info.name
    row.avatar_url = info.picture
    row.raw_profile = json.dumps(info.raw, default=str)
    row.last_login_at = now


async def _upsert_user_from_google(
    db: AsyncSession, info: GoogleUserInfo
) -> tuple[User, bool]:
    """Return ``(user, is_new)`` after applying the upsert rules.

    ``is_new=True`` only when we created a brand-new User row in this
    call; an existing user gaining a Google link returns ``is_new=False``.
    """
    now = datetime.now(timezone.utc)

    # 1. Existing OAuth row → reuse, just refresh profile snapshot.
    existing = await _find_user_by_oauth(
        db, provider=GOOGLE_PROVIDER, provider_user_id=info.sub
    )
    if existing is not None:
        user, row = existing
        if not user.is_active:
            raise HTTPException(status_code=403, detail="account is disabled")
        _refresh_oauth_row(row, info, now)
        user.last_login_at = now
        # Avatar pickup-on-relogin is opt-in; keep the user's local
        # avatar unless they never set one.
        if not user.avatar_url and info.picture:
            user.avatar_url = info.picture
        await db.commit()
        await db.refresh(user)
        return user, False

    # 2. Existing email → link Google to the existing account.
    user = await _find_user_by_email(db, info.email)
    if user is not None:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="account is disabled")
        row = _build_oauth_row(user_id=user.id, info=info, now=now)
        db.add(row)
        # Promote email-verified state if Google confirms it (a password
        # signup that never verified can still get the green tick by
        # signing in via Google once).
        if info.email_verified and not user.is_verified:
            user.is_verified = True
            user.email_verified_at = now
        user.last_login_at = now
        try:
            await db.commit()
        except IntegrityError as exc:
            # Race: another concurrent callback may have inserted the
            # same (provider, provider_user_id) row. Reload and reuse.
            await db.rollback()
            log.warning(
                "google link race for user=%s: %s; reloading", user.email, exc
            )
            existing = await _find_user_by_oauth(
                db, provider=GOOGLE_PROVIDER, provider_user_id=info.sub
            )
            if existing is None:
                raise HTTPException(
                    status_code=500,
                    detail="google login state inconsistent; retry",
                ) from exc
            user, _ = existing
        await db.refresh(user)
        return user, False

    # 3. Brand new — create user + workspace + oauth row.
    user = await _create_user_and_workspace(db, info)
    row = _build_oauth_row(user_id=user.id, info=info, now=now)
    db.add(row)
    user.last_login_at = now
    await db.commit()
    await db.refresh(user)
    return user, True


# ---------------------------------------------------------------------------
# /login — kick off the OAuth dance
# ---------------------------------------------------------------------------


def _ensure_google_configured() -> None:
    """Fail fast with 503 if the operator hasn't supplied Google creds.

    Returning 503 here (rather than letting Authlib bomb with a
    confusing OAuthError) makes the misconfiguration immediately
    obvious in logs.
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "google sign-in is not configured on this deployment; "
                "set SHADOWBLADE_GOOGLE_CLIENT_ID and _SECRET"
            ),
        )


@router.get("/login")
async def google_login(
    request: Request,
    oauth: Annotated[OAuth, Depends(get_google_oauth_client)],
    next_url: Annotated[
        str | None,
        Query(
            alias="next",
            description=(
                "Override the post-login redirect for this single flow. "
                "Must match an allow-list pattern (same origin as "
                "google_post_login_redirect) — otherwise ignored."
            ),
            max_length=512,
        ),
    ] = None,
):
    """302 the browser to Google's consent screen.

    Authlib stashes ``state`` and the PKCE ``code_verifier`` in the
    request's session (cookies via SessionMiddleware). The callback
    verifies state before doing anything else.

    The optional ``next`` parameter is captured into the session so the
    callback knows where to bounce the browser after issuing tokens.
    We never trust it for cross-origin redirects — see
    ``_safe_post_login_redirect``.
    """
    _ensure_google_configured()

    if next_url:
        request.session["google_oauth_next"] = next_url

    try:
        return await oauth.google.authorize_redirect(
            request,
            settings.google_redirect_uri,
        )
    except OAuthError as exc:
        log.exception("authorize_redirect failed: %s", exc)
        raise HTTPException(
            status_code=502, detail=f"google oauth error: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# /callback — exchange code → user → tokens
# ---------------------------------------------------------------------------


def _safe_post_login_redirect(candidate: str | None) -> str:
    """Pick a safe URL to bounce the browser to after a successful login.

    Allow:
    * the configured ``google_post_login_redirect`` (always).
    * any URL whose origin matches ``google_post_login_redirect``'s.

    Reject anything else and fall back to the default — prevents an
    attacker from crafting a ``?next=https://evil.com`` that hijacks
    the freshly-issued token fragment.
    """
    default = settings.google_post_login_redirect
    if not candidate:
        return default
    try:
        from urllib.parse import urlparse

        default_parts = urlparse(default)
        candidate_parts = urlparse(candidate)
    except Exception:  # noqa: BLE001
        return default

    # Same scheme + host + port (port is encoded in netloc) → allowed.
    if (
        candidate_parts.scheme == default_parts.scheme
        and candidate_parts.netloc == default_parts.netloc
    ):
        return candidate
    return default


def _build_fragment_redirect(target: str, payload: dict[str, Any]) -> str:
    """Append the JWT envelope to ``target`` as a URL fragment.

    Fragments are NOT sent to the server on the subsequent fetch, so the
    tokens never appear in access logs at the destination. The frontend
    reads ``window.location.hash`` to extract them.
    """
    frag = urlencode({k: v for k, v in payload.items() if v is not None})
    sep = "&" if "#" in target else "#"
    return f"{target}{sep}{frag}"


@router.get("/callback")
async def google_callback(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    oauth: Annotated[OAuth, Depends(get_google_oauth_client)],
    intent: Annotated[
        str,
        Query(
            description=(
                "``json`` returns a LoginResponse body instead of redirecting. "
                "Default (omitted) bounces back to the frontend with the "
                "token pair in the URL fragment."
            ),
        ),
    ] = "redirect",
):
    """Consume Google's auth code, mint local tokens, bounce/echo.

    Failure modes:
    * 400 — Google sent back an error (``?error=access_denied`` etc.)
            or the userinfo lacked required claims.
    * 401 — state mismatch / code already consumed / Authlib token error.
    * 403 — local account is disabled.
    * 503 — Google integration not configured.
    """
    _ensure_google_configured()

    # Surface Google-reported errors directly — ``error=access_denied``
    # is the common one when the user clicks "Cancel" on the consent
    # screen.
    err = request.query_params.get("error")
    if err:
        raise HTTPException(
            status_code=400,
            detail=f"google denied authorisation: {err}",
        )

    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        log.warning("authorize_access_token failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"google oauth handshake failed: {exc}",
        ) from exc

    try:
        info = extract_userinfo(token)
    except ValueError as exc:
        log.warning("google userinfo extraction failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user, is_new = await _upsert_user_from_google(db, info)

    orgs = await _summarise_user_orgs(db, user.id)
    default_ws = orgs[0].id if orgs else None
    env = _token_envelope(user, default_ws)

    log.info(
        "google_callback: user=%s new=%s default_ws=%s",
        user.email,
        is_new,
        default_ws,
    )

    response_body = GoogleCallbackResponse(
        **env,
        user=UserRead.model_validate(user),
        organizations=orgs,
        default_workspace_id=default_ws,
        is_new_user=is_new,
        provider=GOOGLE_PROVIDER,
    )

    if intent == "json":
        return response_body

    # Redirect mode: bounce to the configured frontend URL with tokens
    # as a fragment.
    next_url = _safe_post_login_redirect(
        request.session.pop("google_oauth_next", None)
    )
    target = _build_fragment_redirect(
        next_url,
        {
            "access_token": env["access_token"],
            "refresh_token": env["refresh_token"],
            "token_type": env["token_type"],
            "expires_in": env["expires_in"],
            "refresh_expires_in": env["refresh_expires_in"],
            "is_new_user": "1" if is_new else "0",
            "provider": GOOGLE_PROVIDER,
        },
    )
    return RedirectResponse(target, status_code=status.HTTP_302_FOUND)


__all__ = ["router"]
