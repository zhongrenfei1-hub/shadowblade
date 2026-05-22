"""Shared FastAPI dependencies — DB session, current user, current org, RBAC.

The dependency tree is intentionally layered so endpoints opt in to as much
auth strictness as they need:

    get_db                          → AsyncSession (always)
    get_current_user_id             → int | None  (legacy header OR JWT)
    get_current_workspace_id        → int         (legacy header OR JWT, with DEMO fallback)
    get_current_user                → User | None (DB row from id)
    require_current_user            → User        (401 if absent)
    get_current_organization        → Workspace   (and verified membership)
    require_role("admin")           → (Workspace, WorkspaceMember) with role ≥ admin

Backward-compat rule: existing callers that pass ``X-User-Id`` and
``X-Workspace-Id`` headers (e.g. brand-kit demo, mix-video showcase, the
React frontend during onboarding) keep working unchanged. New endpoints
that need real auth use :func:`require_current_user` and the role guards.

The JWT path takes priority when both header types are present, so a
fully authenticated client never has its identity overridden by a
forgotten demo header.
"""

from __future__ import annotations

import logging
from typing import Annotated, AsyncIterator

from fastapi import Depends, Header, HTTPException, Path, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.permissions import role_at_least
from app.core.security import TokenError, decode_access_token
from app.models import User, Workspace, WorkspaceMember

log = logging.getLogger("shadowblade.api.deps")

# Demo workspace — used whenever no header and no JWT is present. Matches
# the value returned by ``GET /workspaces/me`` in the auth-stub layer.
# Kept for the brand-kit demo and the showcase frontend.
DEMO_WORKSPACE_ID = 1

# auto_error=False so we don't 401 on routes that *optionally* accept auth
# (the demo brand-kit / mix-video paths). Endpoints that *require* auth
# pull from :func:`require_current_user`, which raises 401 itself.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# DB session
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an :class:`AsyncSession`, ensuring it's closed on exit."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Token decoding
# ---------------------------------------------------------------------------


async def _claims_from_token(
    token: str | None = Depends(_oauth2_scheme),
) -> dict | None:
    """Return decoded JWT claims, or ``None`` if no token is presented.

    Invalid/expired tokens raise 401 here so the failure surfaces at the
    boundary instead of getting silently ignored.
    """
    if not token:
        return None
    try:
        return decode_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# Identity resolution — legacy headers + JWT, both supported.
# ---------------------------------------------------------------------------


async def get_current_user_id(
    claims: Annotated[dict | None, Depends(_claims_from_token)] = None,
    x_user_id: int | None = Header(default=None, alias="X-User-Id"),
) -> int | None:
    """Return the calling user id, or ``None`` when unauthenticated.

    Resolution order:

    1. JWT ``sub`` claim (preferred — implies signed proof).
    2. ``X-User-Id`` header (legacy demo path).

    Endpoints that need a user *must* check for ``None`` themselves; we
    don't 401 here so the brand-kit/mix-video demos keep working without
    auth. Use :func:`require_current_user` for endpoints that must reject
    anonymous calls.
    """
    if claims:
        try:
            return int(claims["sub"])
        except (KeyError, ValueError, TypeError):
            return None
    if x_user_id is not None and x_user_id > 0:
        return x_user_id
    return None


async def get_current_workspace_id(
    claims: Annotated[dict | None, Depends(_claims_from_token)] = None,
    x_workspace_id: int | None = Header(default=None, alias="X-Workspace-Id"),
) -> int:
    """Return the workspace id the request is acting on.

    Resolution order:

    1. ``X-Workspace-Id`` header — explicit override (e.g. multi-org user
       switching teams in the frontend).
    2. JWT ``ws`` claim — set at login to the user's default workspace.
    3. :data:`DEMO_WORKSPACE_ID` fallback so the API works out of the box
       during development.

    Header beats token because a user who belongs to multiple orgs needs
    to pick which one a given API call is for, and the token only carries
    the *default*.
    """
    if x_workspace_id is not None and x_workspace_id > 0:
        return x_workspace_id
    if claims:
        ws = claims.get("ws")
        if isinstance(ws, int) and ws > 0:
            return ws
    return DEMO_WORKSPACE_ID


# ---------------------------------------------------------------------------
# User row loading
# ---------------------------------------------------------------------------


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
) -> User | None:
    """Load the User row for the current id, or ``None`` if unauthenticated.

    Disabled (``is_active=False``) accounts are surfaced as ``None`` to
    prevent further use of a stale token.
    """
    if user_id is None:
        return None
    stmt = select(User).where(User.id == user_id)
    row = (await db.execute(stmt)).scalars().first()
    if row is None or not row.is_active:
        return None
    return row


async def require_current_user(
    user: Annotated[User | None, Depends(get_current_user)],
) -> User:
    """Same as :func:`get_current_user` but 401s when missing/inactive."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ---------------------------------------------------------------------------
# Organization access
# ---------------------------------------------------------------------------


async def _load_membership(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
) -> WorkspaceMember | None:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    return (await db.execute(stmt)).scalars().first()


async def get_current_organization(
    org_id: Annotated[int, Path(alias="org_id")],
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[Workspace, WorkspaceMember]:
    """Resolve the path ``org_id`` into ``(Workspace, WorkspaceMember)``.

    Used by every ``/organizations/{org_id}/...`` endpoint. Raises:

    * 404 if the workspace doesn't exist (don't leak existence to
      non-members).
    * 403 if the user is not a member.

    The membership row is returned alongside the workspace because every
    downstream check needs the role — fetching it twice would be wasteful.
    """
    ws = await db.get(Workspace, org_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="organization not found")
    membership = await _load_membership(
        db, workspace_id=ws.id, user_id=user.id
    )
    if membership is None:
        # 404 instead of 403 to avoid leaking the org's existence to
        # non-members — same convention as GitHub's private repos.
        raise HTTPException(status_code=404, detail="organization not found")
    return ws, membership


def require_role(min_role: str):
    """Return a dependency that enforces ``membership.role >= min_role``.

    Usage::

        @router.delete("/organizations/{org_id}", ...)
        async def delete_org(
            ctx: Annotated[tuple, Depends(require_role("owner"))],
            ...
        ):
            ws, membership = ctx
    """

    async def _dep(
        ctx: Annotated[
            tuple[Workspace, WorkspaceMember], Depends(get_current_organization)
        ],
    ) -> tuple[Workspace, WorkspaceMember]:
        ws, membership = ctx
        if not role_at_least(membership.role, min_role):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"role {membership.role!r} cannot perform this action "
                    f"(requires {min_role}+)"
                ),
            )
        return ws, membership

    # Distinct docstring per call so FastAPI's openapi sees them as
    # separate dependencies (avoids accidental dependency dedup).
    _dep.__doc__ = f"Require workspace role ≥ {min_role}."
    return _dep


# ---------------------------------------------------------------------------
# Header-driven role resolution (settings / brand-kit family)
# ---------------------------------------------------------------------------
#
# The path-driven ``require_role`` above is keyed on a ``{org_id}`` URL
# segment. The settings family is *implicit* about the org (it acts on the
# caller's current workspace via ``X-Workspace-Id``), so we need a parallel
# dependency that resolves role from headers.
#
# Resolution order for :func:`get_effective_workspace_role`:
#
#   1. ``X-Workspace-Role`` header — explicit override used by tests and
#      by service-to-service calls that already know the actor's role.
#   2. ``WorkspaceMember`` row for the (workspace_id, user_id) pair.
#   3. Fallback for the demo workspace (id=1): treat anonymous + unknown
#      users as ``admin`` so the local-dev / showcase flows keep working.
#   4. Otherwise: ``guest``.
#
# Keeping the demo fallback explicit means a misconfigured prod server
# (workspace_id > 1, no membership row) never silently grants admin.


async def get_effective_workspace_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
    x_workspace_role: str | None = Header(default=None, alias="X-Workspace-Role"),
) -> str:
    """Return the role string for the caller in their current workspace."""
    if x_workspace_role:
        # Defensive — the header is meant for tests, but still validate.
        from app.core.permissions import ROLE_HIERARCHY

        if x_workspace_role in ROLE_HIERARCHY:
            return x_workspace_role

    if user_id is not None:
        membership = await _load_membership(
            db, workspace_id=workspace_id, user_id=user_id
        )
        if membership is not None:
            return membership.role

    if workspace_id == DEMO_WORKSPACE_ID:
        return "admin"

    return "guest"


def require_workspace_role(min_role: str):
    """Header-driven equivalent of :func:`require_role`.

    Use on settings endpoints that need admin/owner privileges::

        @router.put("/settings/organization")
        async def put_org(
            role: Annotated[str, Depends(require_workspace_role("admin"))],
            ...
        ):
            ...
    """

    async def _dep(
        role: Annotated[str, Depends(get_effective_workspace_role)],
    ) -> str:
        if not role_at_least(role, min_role):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"role {role!r} cannot perform this action "
                    f"(requires {min_role}+)"
                ),
            )
        return role

    _dep.__doc__ = f"Require workspace role ≥ {min_role} (header-driven)."
    return _dep


def get_request_ip(request: Request) -> str:
    """Best-effort client IP for audit logging. Trusts ``X-Forwarded-For``."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


__all__ = [
    "DEMO_WORKSPACE_ID",
    "get_current_organization",
    "get_current_user",
    "get_current_user_id",
    "get_current_workspace_id",
    "get_db",
    "get_effective_workspace_role",
    "get_request_ip",
    "require_current_user",
    "require_role",
    "require_workspace_role",
]
