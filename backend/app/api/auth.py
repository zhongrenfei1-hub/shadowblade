"""Auth endpoints — register, login, /me, logout, refresh, password reset,
email verification.

The earlier mock at this path returned a hardcoded demo user; this module
replaces it with a real flow modelled after ``fastapi/full-stack-fastapi-
template``:

Public surface (all prefixed with ``/api/v1`` via main.py):

* ``POST /auth/register``              user + personal workspace + token pair
* ``POST /auth/login``                 verify bcrypt → access + refresh
* ``GET  /auth/me``                    current user + org list
* ``POST /auth/logout``                stateless no-op
* ``POST /auth/refresh``               exchange refresh token for new pair
* ``POST /auth/password/change``       authed; rotate password
* ``POST /auth/password/recover``      anon; mint a reset token (dev) or send email (prod)
* ``POST /auth/password/reset``        consume reset token + new password
* ``POST /auth/email/verify``          consume verification token
* ``POST /auth/email/resend-verification``  authed; re-issue verification token

Conventions:

* Identical 401 messages for "no such user" and "wrong password" — prevents
  enumeration of registered accounts.
* The recovery endpoint always returns ``ok=True`` even if the email is
  unknown (same anti-enumeration principle).
* Refresh-token rotation: every ``/auth/refresh`` returns a *new* refresh
  token alongside the new access token. Clients should drop the old one.
* The new-org bootstrap on register matches the convention used by
  fastapi-fullstack-template — every user has at least one workspace, so
  downstream code (brand kit, projects, mix-video) never has to special-
  case the "user with no org" state.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_current_user
from app.core.config import settings
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_password,
    verify_email_verification_token,
    verify_password,
    verify_password_reset_token,
)
from app.models import User, Workspace, WorkspaceMember
from app.schemas.auth import (
    EmailVerificationRequest,
    EmailVerificationResendResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PasswordChangeRequest,
    PasswordRecoverRequest,
    PasswordRecoverResponse,
    PasswordResetRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterResponse,
)
from app.schemas.organization import OrganizationSummary
from app.schemas.user import UserCreate, UserRead, validate_username

log = logging.getLogger("shadowblade.api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SLUG_FALLBACK_RE = re.compile(r"[^a-z0-9]+")
_USERNAME_FALLBACK_RE = re.compile(r"[^a-z0-9_.]+")


def _slug_from_email(email: str) -> str:
    """Derive a workspace slug from an email's local part.

    Example: ``ava.chen@acme.com`` → ``ava-chen``. The DB layer enforces
    uniqueness via the unique constraint on ``workspaces.slug``; the API
    appends a short random suffix on collision.
    """
    local = email.split("@", 1)[0].lower()
    base = _SLUG_FALLBACK_RE.sub("-", local).strip("-")
    if not base:
        base = "team"
    if len(base) < 2:
        base = base + "x"
    return base[:32]


def _username_from_email(email: str) -> str:
    """Derive a username from an email's local part.

    Looser than the slug derivation because usernames allow ``_`` and ``.``
    natively. Falls back to ``user`` for pathological inputs (the API then
    appends a unique suffix on collision).
    """
    local = email.split("@", 1)[0].lower()
    cleaned = _USERNAME_FALLBACK_RE.sub("", local).strip("._")
    if not cleaned or not cleaned[0].isalpha():
        cleaned = "user" + (cleaned or "")
    return cleaned[:48]


async def _allocate_unique_username(db: AsyncSession, base: str) -> str:
    """Return ``base`` or ``base{N}`` such that no User row has it."""
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


def _token_envelope(user: User, default_ws: int | None) -> dict:
    """Mint an access + refresh pair for ``user``.

    The access token carries the workspace context (``ws`` claim) so
    follow-up calls can act on the right org without a header. Refresh
    tokens stay minimal — they only need to prove identity for the
    ``/auth/refresh`` exchange.
    """
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


async def _allocate_unique_slug(db: AsyncSession, base: str) -> str:
    """Return ``base`` or ``base-N`` such that no Workspace row has it."""
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


async def _load_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Case-insensitive lookup by email."""
    return (
        await db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
    ).scalars().first()


async def _load_user_by_identifier(
    db: AsyncSession, identifier: str
) -> User | None:
    """Resolve an email *or* username into a User row.

    Tries email first (it's more common in our forms), then username.
    Case-insensitive in both directions.
    """
    ident = identifier.strip()
    if "@" in ident:
        return await _load_user_by_email(db, ident)
    return (
        await db.execute(
            select(User).where(func.lower(User.username) == ident.lower())
        )
    ).scalars().first()


# ---------------------------------------------------------------------------
# Endpoints — register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a user + their personal workspace; return a token pair.

    On collision (email already exists) we return 409 — never reveal
    whether *just the email* exists vs *email+password matches* (that's
    what /login is for).
    """
    existing = await _load_user_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="an account with this email already exists"
        )

    if payload.username is not None:
        clash = (
            await db.execute(
                select(User.id).where(User.username == payload.username)
            )
        ).first()
        if clash is not None:
            raise HTTPException(
                status_code=409, detail="username is already taken"
            )
        username = payload.username
    else:
        base = _username_from_email(payload.email)
        try:
            base = validate_username(base)
        except ValueError:
            base = "user"
        username = await _allocate_unique_username(db, base)

    user = User(
        email=payload.email,
        username=username,
        full_name=payload.full_name,
        avatar_url=payload.avatar_url,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_verified=False,
        last_password_change_at=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="email or username collision; please retry"
        ) from exc

    base_slug = _slug_from_email(payload.email)
    slug = await _allocate_unique_slug(db, base_slug)
    ws = Workspace(
        slug=slug,
        name=f"{payload.full_name} 的团队",
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
    await db.commit()
    await db.refresh(user)
    await db.refresh(ws)

    verification_token = generate_email_verification_token(user.email)

    log.info(
        "register: user=%s username=%s slug=%s workspace=%s",
        user.email,
        user.username,
        ws.slug,
        ws.id,
    )

    env = _token_envelope(user, default_ws=ws.id)
    orgs = await _summarise_user_orgs(db, user.id)
    return RegisterResponse(
        **env,
        user=UserRead.model_validate(user),
        organizations=orgs,
        default_workspace_id=ws.id,
        new_organization_id=ws.id,
        email_verification_token=verification_token,
    )


# ---------------------------------------------------------------------------
# Endpoints — login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate with email/username + password.

    Accepts:

    * ``application/json``                — ``{"email":..., "password":...}``
    * ``application/x-www-form-urlencoded`` — OAuth2 password flow
      (``username``, ``password``); we treat ``username`` as either an
      email or a real username, resolved by ``_load_user_by_identifier``.

    Returns an access + refresh pair + the user record + their org
    memberships. The default workspace claim on the access token is the
    owner-most / oldest org.
    """
    ct = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    identifier: str
    password: str
    if ct == "application/json":
        body = await request.json()
        try:
            req = LoginRequest(**(body or {}))
        except Exception as exc:  # noqa: BLE001 — pydantic ValidationError
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        identifier = req.email
        password = req.password
    elif ct in {
        "application/x-www-form-urlencoded",
        "multipart/form-data",
    }:
        form = await request.form()
        identifier = str(form.get("username") or form.get("email") or "")
        password = str(form.get("password") or "")
        if not identifier or not password:
            raise HTTPException(
                status_code=422, detail="username/email and password required"
            )
    else:
        try:
            body = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=415, detail=f"unsupported content-type {ct!r}"
            ) from exc
        req = LoginRequest(**(body or {}))
        identifier = req.email
        password = req.password

    user = await _load_user_by_identifier(db, identifier)
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="account is disabled")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    orgs = await _summarise_user_orgs(db, user.id)
    default_ws = orgs[0].id if orgs else None
    env = _token_envelope(user, default_ws)

    return LoginResponse(
        **env,
        user=UserRead.model_validate(user),
        organizations=orgs,
        default_workspace_id=default_ws,
    )


# ---------------------------------------------------------------------------
# Endpoints — /me, logout
# ---------------------------------------------------------------------------


@router.get("/me", response_model=LoginResponse)
async def me(
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return the current user + their org memberships.

    Shaped like :class:`LoginResponse` (minus the token contents) so the
    React frontend can use a single component for both post-login state
    and post-refresh state. The token fields are empty because /me should
    never be used to *issue* tokens — refresh goes through /auth/refresh.
    """
    orgs = await _summarise_user_orgs(db, user.id)
    default_ws = orgs[0].id if orgs else None
    return LoginResponse(
        access_token="",
        token_type="bearer",
        expires_in=0,
        refresh_token="",
        refresh_expires_in=0,
        user=UserRead.model_validate(user),
        organizations=orgs,
        default_workspace_id=default_ws,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """Stateless logout — clients drop the token themselves.

    Kept for interface compatibility with the previous demo router; in a
    revoke-list future this would write to a deny table.
    """
    return MessageResponse(ok=True, message="logged out")


# ---------------------------------------------------------------------------
# Endpoints — refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Exchange a refresh token for a fresh access + refresh pair.

    Refresh-token rotation: the response includes a *new* refresh token
    that the client should store, dropping the old one. This limits the
    blast radius of a leaked refresh token.

    Returns 401 for any failure — expired, malformed, wrong-type token,
    or a user that no longer exists / is disabled.
    """
    try:
        claims = decode_refresh_token(payload.refresh_token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = int(claims["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalars().first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not available",
            headers={"WWW-Authenticate": "Bearer"},
        )

    orgs = await _summarise_user_orgs(db, user.id)
    default_ws = orgs[0].id if orgs else None
    env = _token_envelope(user, default_ws)
    return RefreshResponse(**env)


# ---------------------------------------------------------------------------
# Endpoints — password change (authenticated)
# ---------------------------------------------------------------------------


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    payload: PasswordChangeRequest,
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Rotate the logged-in user's password.

    Requires the *current* password to be presented even though the user
    is already authenticated — defence against session hijack. Returns
    401 (not 400) on wrong current-password so it can't be used to probe
    a borrowed token's validity.
    """
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="current password is incorrect",
        )
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="new password must differ from the current one",
        )

    user.hashed_password = hash_password(payload.new_password)
    user.last_password_change_at = datetime.now(timezone.utc)
    await db.commit()
    log.info("password changed: user=%s", user.email)
    return MessageResponse(ok=True, message="password updated")


# ---------------------------------------------------------------------------
# Endpoints — password recovery (forgot password)
# ---------------------------------------------------------------------------


@router.post("/password/recover", response_model=PasswordRecoverResponse)
async def recover_password(
    payload: PasswordRecoverRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Initiate the forgot-password flow.

    Always returns ``ok=True`` even when the email doesn't match a user —
    prevents enumeration of registered emails. In dev mode the reset
    token is returned in the response body so the showcase frontend and
    tests can drive the reset flow without a real email provider; the
    production build should drop ``reset_token`` from the response and
    instead send the link via email.
    """
    user = await _load_user_by_email(db, payload.email)
    if user is None or not user.is_active:
        log.info(
            "recover_password: no-op for email=%s (unknown or disabled)",
            payload.email,
        )
        return PasswordRecoverResponse(
            ok=True,
            message="if the email is registered, a reset link has been sent",
            reset_token=None,
        )

    token = generate_password_reset_token(user.email)
    log.info("recover_password: token issued for email=%s", user.email)
    return PasswordRecoverResponse(
        ok=True,
        message="if the email is registered, a reset link has been sent",
        reset_token=token if settings.environment != "production" else None,
    )


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    payload: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Consume a password-reset token + set a new password.

    Failure modes:
    * 401 — token invalid/expired/wrong-type.
    * 404 — token valid but the user has since been deleted/disabled.
    * 400 — new password identical to current (no-op rotation).
    """
    try:
        email = verify_password_reset_token(payload.token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user = await _load_user_by_email(db, email)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="user not found or disabled")

    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="new password must differ from the current one",
        )

    user.hashed_password = hash_password(payload.new_password)
    user.last_password_change_at = datetime.now(timezone.utc)
    await db.commit()
    log.info("password reset complete: user=%s", user.email)
    return MessageResponse(ok=True, message="password updated")


# ---------------------------------------------------------------------------
# Endpoints — email verification
# ---------------------------------------------------------------------------


@router.post("/email/verify", response_model=MessageResponse)
async def verify_email(
    payload: EmailVerificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Consume an email verification token.

    Idempotent — if the user is already verified, returns ``ok=True``
    with a different message instead of an error. That makes the
    success page on the frontend tolerant to refreshes.
    """
    try:
        email = verify_email_verification_token(payload.token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user = await _load_user_by_email(db, email)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    if user.is_verified:
        return MessageResponse(ok=True, message="email already verified")

    user.is_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()
    log.info("email verified: user=%s", user.email)
    return MessageResponse(ok=True, message="email verified")


@router.post(
    "/email/resend-verification",
    response_model=EmailVerificationResendResponse,
)
async def resend_email_verification(
    user: Annotated[User, Depends(require_current_user)],
):
    """Re-issue an email verification token for the current user.

    Requires an active session so we don't become an open spam relay.
    Returns ``message`` indicating that the email is on the way; in dev
    mode the token is also surfaced for tests/showcases.
    """
    if user.is_verified:
        return EmailVerificationResendResponse(
            ok=True,
            message="email is already verified",
            verification_token=None,
        )

    token = generate_email_verification_token(user.email)
    log.info("verification email resent: user=%s", user.email)
    return EmailVerificationResendResponse(
        ok=True,
        message="verification email sent",
        verification_token=token if settings.environment != "production" else None,
    )


__all__ = ["router"]
