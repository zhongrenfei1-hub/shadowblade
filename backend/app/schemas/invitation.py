"""WorkspaceInvite — Pydantic V2 schemas.

Two distinct response shapes serve two audiences:

* :class:`InvitationRead`   — full record returned to org admins.
* :class:`InvitationPublic` — sanitised record returned to anonymous
  callers who landed on ``GET /invitations/{code}``. Hides the inviter's
  identity and the workspace id details to limit recon if a code leaks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.permissions import ALLOWED_ROLES, normalize_role
from app.schemas.user import UserPublic

InviteStatus = Literal["pending", "accepted", "revoked", "expired"]
InviteRole = Literal["admin", "member", "guest"]
# ``owner`` is intentionally excluded — there's only one and they own it
# from creation. Promotion to owner goes through /transfer instead.


_ALLOWED_INVITE_ROLES = {"admin", "member", "guest"}


def _coerce_invite_role(v: object) -> str:
    """Normalise + reject owner. Mirrors the membership coercer."""
    if not isinstance(v, str):
        raise ValueError("role must be a string")
    canonical = normalize_role(v)
    if canonical not in _ALLOWED_INVITE_ROLES:
        raise ValueError(
            f"role must be one of admin|member|guest "
            f"(aliases: editor=member, viewer=guest); got {v!r}"
        )
    return canonical


class InvitationCreate(BaseModel):
    """``POST /organizations/{org_id}/invitations`` body."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    role: InviteRole = "member"
    # Optional override for the default TTL of 14 days. Capped at 90 to
    # keep a stale token from lingering indefinitely. ``0`` = use server
    # default.
    expires_in_days: int = Field(default=14, ge=1, le=90)

    @field_validator("role", mode="before")
    @classmethod
    def _role_allowed(cls, v: object) -> str:
        return _coerce_invite_role(v)


class InvitationRead(BaseModel):
    """Full record — admin view."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    email: EmailStr
    role: str
    invite_code: str
    status: str
    invited_by: int | None = None
    inviter: UserPublic | None = None
    expires_at: datetime | None = None
    accepted_at: datetime | None = None
    accepted_by: int | None = None
    created_at: datetime | None = None


class InvitationPublic(BaseModel):
    """Sanitised record — what an anonymous code-holder sees.

    No inviter identity, no email. The frontend uses this to render the
    "You've been invited to <org name>" landing page before login.
    """

    model_config = ConfigDict(from_attributes=True)

    invite_code: str
    workspace_id: int
    workspace_name: str | None = None  # filled in the API layer by joining
    role: str
    status: str
    expires_at: datetime | None = None
    email: EmailStr  # the addressee — so the landing page can pre-fill


class InvitationAcceptResponse(BaseModel):
    """Returned from ``POST /invitations/{code}/accept``."""

    membership_id: int
    workspace_id: int
    role: str
    accepted_at: datetime


__all__ = [
    "InvitationAcceptResponse",
    "InvitationCreate",
    "InvitationPublic",
    "InvitationRead",
    "InviteRole",
    "InviteStatus",
]
