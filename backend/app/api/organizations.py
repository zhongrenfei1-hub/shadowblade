"""REST endpoints for Team/Organization management.

URL surface::

    GET    /organizations                                  list user's orgs
    POST   /organizations                                  create new org (caller=owner)
    GET    /organizations/{org_id}                         org detail
    PATCH  /organizations/{org_id}                         update org (admin+)
    DELETE /organizations/{org_id}                         delete org (owner)

    GET    /organizations/{org_id}/members                 list members
    POST   /organizations/{org_id}/members                 direct add (admin+)
    PUT    /organizations/{org_id}/members/{user_id}       change role (admin+)
    DELETE /organizations/{org_id}/members/{user_id}       remove (admin+ or self)
    POST   /organizations/{org_id}/transfer                transfer ownership (owner)

    GET    /organizations/{org_id}/invitations             list invites (admin+)
    POST   /organizations/{org_id}/invitations             create invite (admin+)
    DELETE /organizations/{org_id}/invitations/{id}        revoke (admin+)

    GET    /invitations/{code}                             inspect (public)
    POST   /invitations/{code}/accept                      accept (auth required)

Invariants enforced here, not in the DB:

* Exactly one owner per organization at all times.
* Owner cannot be removed without first being downgraded via /transfer.
* Demoting yourself works *unless* you are the sole owner.
* An invite is "live" only when status='pending' AND expires_at > now.
* A user can hold at most one membership row per organization (DB
  UniqueConstraint enforces it; the API catches the IntegrityError and
  surfaces 409 instead of 500).
"""

from __future__ import annotations

import logging
import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_organization,
    get_db,
    require_current_user,
    require_role,
)
from app.core.permissions import assert_role_value, role_at_least
from app.models import (
    User,
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
)
from app.schemas.invitation import (
    InvitationAcceptResponse,
    InvitationCreate,
    InvitationPublic,
    InvitationRead,
)
from app.schemas.membership import (
    MembershipCreate,
    MembershipRead,
    MembershipUpdate,
    TransferOwnership,
)
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.schemas.user import UserPublic

log = logging.getLogger("shadowblade.api.organizations")
router = APIRouter(tags=["organizations"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _decorate_org_read(
    ws: Workspace, *, role: str | None = None, member_count: int | None = None
) -> OrganizationRead:
    """ORM Workspace → response model with optional caller context."""
    return OrganizationRead.model_validate(
        {
            **{c.name: getattr(ws, c.name) for c in ws.__table__.columns},
            "role": role,
            "member_count": member_count,
        }
    )


async def _member_count(db: AsyncSession, workspace_id: int) -> int:
    stmt = select(func.count(WorkspaceMember.id)).where(
        WorkspaceMember.workspace_id == workspace_id
    )
    return int((await db.execute(stmt)).scalar() or 0)


async def _load_member_row(
    db: AsyncSession, *, workspace_id: int, user_id: int
) -> WorkspaceMember | None:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    )
    return (await db.execute(stmt)).scalars().first()


async def _owner_count(db: AsyncSession, workspace_id: int) -> int:
    stmt = select(func.count(WorkspaceMember.id)).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.role == "owner",
    )
    return int((await db.execute(stmt)).scalar() or 0)


def _generate_invite_code() -> str:
    """32-char URL-safe token, ~192 bits of entropy."""
    return _secrets.token_urlsafe(24)


def _expire_status(invite: WorkspaceInvite) -> str:
    """Resolve the *effective* status given expires_at vs now.

    Pending invites whose ``expires_at`` is in the past get reported as
    ``expired``. Persisting that flip is the caller's responsibility.
    """
    if invite.status == "pending" and invite.expires_at <= _now().replace(tzinfo=None):
        return "expired"
    return invite.status


# ---------------------------------------------------------------------------
# Org CRUD
# ---------------------------------------------------------------------------


@router.get("/organizations", response_model=list[OrganizationRead])
async def list_organizations(
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List every workspace the current user is a member of.

    Sorted by creation date (oldest first) — matches the "default" picked
    by the auth layer at login time.
    """
    stmt = (
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    out: list[OrganizationRead] = []
    for ws, role in rows:
        out.append(
            _decorate_org_read(
                ws,
                role=role,
                member_count=await _member_count(db, ws.id),
            )
        )
    return out


@router.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    payload: OrganizationCreate,
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new org and make the caller its owner.

    409 on slug collision — the slug is part of the public URL surface so
    the user should pick another, not have one quietly mutated.
    """
    existing = (
        await db.execute(select(Workspace).where(Workspace.slug == payload.slug))
    ).scalars().first()
    if existing is not None:
        raise HTTPException(
            status_code=409, detail=f"slug {payload.slug!r} is already taken"
        )

    ws = Workspace(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        avatar_url=payload.avatar_url,
        owner_id=user.id,
        plan=payload.plan,
        seats=payload.seats,
        monthly_render_quota=payload.monthly_render_quota,
    )
    db.add(ws)
    await db.flush()

    membership = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(ws)

    log.info(
        "organization created id=%s slug=%s owner=%s", ws.id, ws.slug, user.id
    )

    return _decorate_org_read(ws, role="owner", member_count=1)


@router.get("/organizations/{org_id}", response_model=OrganizationRead)
async def get_organization(
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(get_current_organization)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return org detail + the caller's role + total member count."""
    ws, membership = ctx
    return _decorate_org_read(
        ws,
        role=membership.role,
        member_count=await _member_count(db, ws.id),
    )


@router.patch("/organizations/{org_id}", response_model=OrganizationRead)
async def update_organization(
    payload: OrganizationUpdate,
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("admin"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update mutable org fields. Plan/quota changes require owner-level."""
    ws, membership = ctx
    patch = payload.model_dump(exclude_unset=True)

    # Plan + quota are billing-y; require owner.
    billing_keys = {"plan", "seats", "monthly_render_quota"}
    if billing_keys & patch.keys() and not role_at_least(membership.role, "owner"):
        raise HTTPException(
            status_code=403,
            detail="plan, seats and quota changes require the owner role",
        )

    for key, value in patch.items():
        setattr(ws, key, value)
    await db.commit()
    await db.refresh(ws)
    return _decorate_org_read(
        ws,
        role=membership.role,
        member_count=await _member_count(db, ws.id),
    )


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("owner"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete the org and cascade-remove its members and invitations.

    Hard-delete is fine here because Project/Asset/BrandKit have ``ON
    DELETE`` set to ``CASCADE`` through the unique-constraint-less SQLite
    schema or to NO ACTION (which becomes ``RESTRICT``) on Postgres — if a
    deletion fails on Postgres, the user gets a 409 with the underlying
    integrity error. Members + invites cascade explicitly via the
    relationship config.
    """
    ws, _ = ctx
    await db.delete(ws)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=(
                "organization has dependent resources (projects, brand kits, "
                "renders); delete or move them before deleting the org"
            ),
        ) from exc


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get(
    "/organizations/{org_id}/members",
    response_model=list[MembershipRead],
)
async def list_members(
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(get_current_organization)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List every member in the org.

    Members in any role can see this list — it's the same scope as the
    workspace itself.
    """
    ws, _ = ctx
    stmt = (
        select(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == ws.id)
        .options(selectinload(WorkspaceMember.user))
        .order_by(
            # Owners first, then descending role power, then by join time.
            WorkspaceMember.role.desc(),
            WorkspaceMember.joined_at.asc(),
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        MembershipRead(
            id=r.id,
            workspace_id=r.workspace_id,
            user_id=r.user_id,
            role=r.role,
            invited_by=r.invited_by,
            joined_at=r.joined_at,
            user=UserPublic.model_validate(r.user) if r.user else None,
        )
        for r in rows
    ]


@router.post(
    "/organizations/{org_id}/members",
    response_model=MembershipRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    payload: MembershipCreate,
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("admin"))
    ],
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Directly add an existing user (no email invite step).

    Used by admins who already know the user's id (e.g. internal tooling).
    For the standard onboarding flow use ``POST /invitations`` instead.

    Only ``owner`` can create another ``owner`` — admins cannot
    self-elevate by adding a peer at owner level.
    """
    ws, actor_membership = ctx
    target_role = assert_role_value(payload.role)

    if target_role == "owner" and not role_at_least(actor_membership.role, "owner"):
        raise HTTPException(
            status_code=403, detail="only an owner can grant the owner role"
        )

    # Make sure the target user exists.
    target_user = await db.get(User, payload.user_id)
    if target_user is None or not target_user.is_active:
        raise HTTPException(status_code=404, detail="target user not found")

    # Prevent duplicate membership rows up-front for a nicer error.
    existing = await _load_member_row(
        db, workspace_id=ws.id, user_id=target_user.id
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="user is already a member of this organization",
        )

    row = WorkspaceMember(
        workspace_id=ws.id,
        user_id=target_user.id,
        role=target_role,
        invited_by=user.id,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="duplicate membership row"
        ) from exc
    await db.refresh(row)

    return MembershipRead(
        id=row.id,
        workspace_id=row.workspace_id,
        user_id=row.user_id,
        role=row.role,
        invited_by=row.invited_by,
        joined_at=row.joined_at,
        user=UserPublic.model_validate(target_user),
    )


@router.put(
    "/organizations/{org_id}/members/{user_id}",
    response_model=MembershipRead,
)
async def update_member_role(
    user_id: int,
    payload: MembershipUpdate,
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("admin"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change a member's role.

    Invariants:

    * Admins cannot promote anyone to ``owner`` — only the current owner
      can, and that path is reserved for ``POST /transfer``.
    * The sole owner cannot demote themselves; transfer first.
    * An admin cannot demote another admin to ``guest`` or below without
      being an owner (prevents lateral attacks).
    """
    ws, actor_membership = ctx
    target_role = assert_role_value(payload.role)

    target = await _load_member_row(db, workspace_id=ws.id, user_id=user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="member not found")

    # Promotion to owner blocked here; use /transfer.
    if target_role == "owner":
        raise HTTPException(
            status_code=400,
            detail="use POST /organizations/{org_id}/transfer to assign owner",
        )

    # Demoting an existing owner triggers the sole-owner check.
    if target.role == "owner" and target_role != "owner":
        owners = await _owner_count(db, ws.id)
        if owners <= 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "cannot demote the only owner; transfer ownership first"
                ),
            )

    # Admin trying to mess with another admin needs to be owner.
    if (
        target.role == "admin"
        and not role_at_least(actor_membership.role, "owner")
        and target.user_id != actor_membership.user_id
    ):
        raise HTTPException(
            status_code=403,
            detail="only owners can change the role of another admin",
        )

    target.role = target_role
    await db.commit()
    await db.refresh(target)

    return MembershipRead(
        id=target.id,
        workspace_id=target.workspace_id,
        user_id=target.user_id,
        role=target.role,
        invited_by=target.invited_by,
        joined_at=target.joined_at,
        user=UserPublic.model_validate(target.user) if target.user else None,
    )


@router.delete(
    "/organizations/{org_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    user_id: int,
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(get_current_organization)
    ],
    actor: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a member.

    Allowed when:

    * actor is an admin/owner removing anyone except the sole owner, OR
    * actor is removing themselves (the "leave organization" path).

    Removing yourself when you're the sole owner is refused — transfer
    ownership first.
    """
    ws, actor_membership = ctx
    target = await _load_member_row(db, workspace_id=ws.id, user_id=user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="member not found")

    is_self = target.user_id == actor.id
    can_remove_others = role_at_least(actor_membership.role, "admin")
    if not is_self and not can_remove_others:
        raise HTTPException(
            status_code=403,
            detail="only admins and owners can remove other members",
        )

    # Sole-owner protection.
    if target.role == "owner":
        owners = await _owner_count(db, ws.id)
        if owners <= 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "cannot remove the only owner; transfer ownership first"
                ),
            )

    # Admin trying to remove another admin requires owner privilege
    # (prevents an admin coup).
    if (
        target.role == "admin"
        and not is_self
        and not role_at_least(actor_membership.role, "owner")
    ):
        raise HTTPException(
            status_code=403,
            detail="only an owner can remove another admin",
        )

    await db.delete(target)
    await db.commit()


@router.post(
    "/organizations/{org_id}/transfer",
    response_model=list[MembershipRead],
)
async def transfer_ownership(
    payload: TransferOwnership,
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("owner"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Move the owner role to another existing member.

    The previous owner is demoted to ``admin`` (least-surprise default).
    Returns the two affected membership rows so the UI can update both
    seats without a refetch.
    """
    ws, actor_membership = ctx
    if payload.new_owner_id == actor_membership.user_id:
        raise HTTPException(
            status_code=400, detail="you are already the owner"
        )

    new_owner = await _load_member_row(
        db, workspace_id=ws.id, user_id=payload.new_owner_id
    )
    if new_owner is None:
        raise HTTPException(
            status_code=404,
            detail="target user is not a member of this organization",
        )

    actor_membership.role = "admin"
    new_owner.role = "owner"
    ws.owner_id = new_owner.user_id
    await db.commit()
    await db.refresh(actor_membership)
    await db.refresh(new_owner)

    def _to_read(m: WorkspaceMember) -> MembershipRead:
        return MembershipRead(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role,
            invited_by=m.invited_by,
            joined_at=m.joined_at,
            user=UserPublic.model_validate(m.user) if m.user else None,
        )

    return [_to_read(new_owner), _to_read(actor_membership)]


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.get(
    "/organizations/{org_id}/invitations",
    response_model=list[InvitationRead],
)
async def list_invitations(
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("admin"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all invitations for the org (any status).

    Pending invites whose ``expires_at`` has passed are reported as
    ``expired`` in the response, even if the DB still has them ``pending``
    — a background job will eventually flip the column.
    """
    ws, _ = ctx
    stmt = (
        select(WorkspaceInvite)
        .where(WorkspaceInvite.workspace_id == ws.id)
        .options(selectinload(WorkspaceInvite.inviter))
        .order_by(WorkspaceInvite.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    out: list[InvitationRead] = []
    for inv in rows:
        effective_status = _expire_status(inv)
        out.append(
            InvitationRead(
                id=inv.id,
                workspace_id=inv.workspace_id,
                email=inv.email,
                role=inv.role,
                invite_code=inv.invite_code,
                status=effective_status,
                invited_by=inv.invited_by,
                inviter=(
                    UserPublic.model_validate(inv.inviter) if inv.inviter else None
                ),
                expires_at=inv.expires_at,
                accepted_at=inv.accepted_at,
                accepted_by=inv.accepted_by,
                created_at=inv.created_at,
            )
        )
    return out


@router.post(
    "/organizations/{org_id}/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: InvitationCreate,
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("admin"))
    ],
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Issue a new invitation. The invite code is the secret token.

    If the email already corresponds to a member of this org, we return
    409 to avoid spamming someone with redundant invites. A previous
    pending invite for the same email is *not* revoked automatically —
    admins can have multiple live invites for the same address if they
    wish (e.g. resending) and revoke explicitly via ``DELETE``.
    """
    ws, _ = ctx

    # If the email already belongs to a member, short-circuit with 409.
    member_check_stmt = (
        select(WorkspaceMember.id)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == ws.id,
            func.lower(User.email) == payload.email.lower(),
        )
    )
    if (await db.execute(member_check_stmt)).first() is not None:
        raise HTTPException(
            status_code=409,
            detail="that user is already a member of this organization",
        )

    code = _generate_invite_code()
    expires_at = _now().replace(tzinfo=None) + timedelta(days=payload.expires_in_days)
    invite = WorkspaceInvite(
        workspace_id=ws.id,
        email=payload.email,
        role=payload.role,
        invite_code=code,
        invited_by=user.id,
        status="pending",
        expires_at=expires_at,
    )
    db.add(invite)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # Code collision is astronomically rare with 192 bits, but handle.
        raise HTTPException(
            status_code=500, detail="invite code collision; retry"
        ) from exc
    await db.refresh(invite)

    log.info(
        "invite created id=%s ws=%s email=%s role=%s by=%s",
        invite.id,
        ws.id,
        payload.email,
        payload.role,
        user.id,
    )

    return InvitationRead(
        id=invite.id,
        workspace_id=invite.workspace_id,
        email=invite.email,
        role=invite.role,
        invite_code=invite.invite_code,
        status=invite.status,
        invited_by=invite.invited_by,
        inviter=UserPublic.model_validate(user),
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        accepted_by=invite.accepted_by,
        created_at=invite.created_at,
    )


@router.delete(
    "/organizations/{org_id}/invitations/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_invitation(
    invite_id: int,
    ctx: Annotated[
        tuple[Workspace, WorkspaceMember], Depends(require_role("admin"))
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mark a pending invite as revoked.

    No-op + 404 if the invite doesn't exist in this org. Idempotent on
    already-revoked invites (returns 204 either way).
    """
    ws, _ = ctx
    invite = await db.get(WorkspaceInvite, invite_id)
    if invite is None or invite.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="invitation not found")
    if invite.status != "revoked":
        invite.status = "revoked"
        await db.commit()


# ---------------------------------------------------------------------------
# Public invite endpoints (no org membership required)
# ---------------------------------------------------------------------------


@router.get("/invitations/{code}", response_model=InvitationPublic)
async def inspect_invitation(
    code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Anonymous endpoint — used by the "you've been invited" landing page.

    Reveals minimum context (org name, role, expiry) so the recipient can
    decide whether to register/login and accept. Hides inviter identity.
    """
    stmt = (
        select(WorkspaceInvite, Workspace.name)
        .join(Workspace, Workspace.id == WorkspaceInvite.workspace_id)
        .where(WorkspaceInvite.invite_code == code)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="invitation not found")
    invite, workspace_name = row
    return InvitationPublic(
        invite_code=invite.invite_code,
        workspace_id=invite.workspace_id,
        workspace_name=workspace_name,
        role=invite.role,
        status=_expire_status(invite),
        expires_at=invite.expires_at,
        email=invite.email,
    )


@router.post(
    "/invitations/{code}/accept",
    response_model=InvitationAcceptResponse,
)
async def accept_invitation(
    code: str,
    user: Annotated[User, Depends(require_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Accept an invite — create the WorkspaceMember row.

    Strict invariants:

    * Status must be ``pending`` *and* not expired (we flip ``expired``
      transparently here so subsequent calls are deterministic).
    * The invitation email must match the authenticated user's email
      (case-insensitive). Otherwise 403 — invitations are addressee-bound.
    * If the user is already a member, we return 409 *and* mark the
      invite as accepted (idempotent for the user, accurate for audit).
    """
    invite = (
        await db.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.invite_code == code)
        )
    ).scalars().first()
    if invite is None:
        raise HTTPException(status_code=404, detail="invitation not found")

    # Status normalisation — flip to expired in the DB if the date is past.
    if invite.status == "pending" and invite.expires_at <= _now().replace(
        tzinfo=None
    ):
        invite.status = "expired"
        await db.commit()
        await db.refresh(invite)

    if invite.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"invitation is {invite.status}, cannot accept",
        )

    if invite.email.lower() != user.email.lower():
        raise HTTPException(
            status_code=403,
            detail=(
                "this invitation was issued to a different email; "
                "log in as the intended recipient"
            ),
        )

    existing = await _load_member_row(
        db, workspace_id=invite.workspace_id, user_id=user.id
    )
    if existing is not None:
        # Already a member — mark the invite accepted for audit and surface 409.
        invite.status = "accepted"
        invite.accepted_at = _now().replace(tzinfo=None)
        invite.accepted_by = user.id
        await db.commit()
        raise HTTPException(
            status_code=409, detail="already a member of this organization"
        )

    membership = WorkspaceMember(
        workspace_id=invite.workspace_id,
        user_id=user.id,
        role=invite.role,
        invited_by=invite.invited_by,
    )
    db.add(membership)

    invite.status = "accepted"
    invite.accepted_at = _now().replace(tzinfo=None)
    invite.accepted_by = user.id

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="race: already a member"
        ) from exc
    await db.refresh(membership)

    log.info(
        "invite accepted ws=%s user=%s role=%s",
        invite.workspace_id,
        user.id,
        invite.role,
    )

    return InvitationAcceptResponse(
        membership_id=membership.id,
        workspace_id=membership.workspace_id,
        role=membership.role,
        accepted_at=invite.accepted_at,
    )


__all__ = ["router"]
