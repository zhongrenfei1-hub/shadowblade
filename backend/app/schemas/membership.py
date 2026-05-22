"""WorkspaceMember — Pydantic V2 schemas.

The fields here mirror :class:`app.models.membership.WorkspaceMember` but
expose the joined user as a nested :class:`UserPublic` so the frontend
never has to follow a second request to render a member list.

Role validation is centralised in :mod:`app.core.permissions` — the schema
just rejects unknown values at the boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.permissions import ALLOWED_ROLES, normalize_role
from app.schemas.user import UserPublic

# Canonical role names. The input validators below also accept the
# legacy ``editor``/``viewer`` aliases from the React frontend and
# normalise them to ``member``/``guest`` before they hit the DB.
MemberRole = Literal["owner", "admin", "member", "guest"]


def _coerce_role(v: object) -> str:
    """Normalise + validate a role string at the boundary.

    Accepts canonical names *and* the ``editor``/``viewer`` aliases so
    the frontend term-of-art (which predates the Team feature) keeps
    working. Anything else 422s with a clear message.
    """
    if not isinstance(v, str):
        raise ValueError("role must be a string")
    canonical = normalize_role(v)
    if canonical not in ALLOWED_ROLES:
        raise ValueError(
            f"role must be one of {sorted(ALLOWED_ROLES)} "
            f"(aliases: editor=member, viewer=guest); got {v!r}"
        )
    return canonical


class MembershipBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: MemberRole = "member"

    @field_validator("role", mode="before")
    @classmethod
    def _role_allowed(cls, v: object) -> str:
        return _coerce_role(v)


class MembershipCreate(MembershipBase):
    """``POST /organizations/{org_id}/members`` body.

    The ``user_id`` is the *target* user being added. The acting user is
    inferred from the JWT. Used for direct-add by an existing admin —
    invitation-based onboarding goes through ``WorkspaceInvite`` instead.
    """

    user_id: int = Field(gt=0)


class MembershipUpdate(BaseModel):
    """``PUT /organizations/{org_id}/members/{user_id}`` body.

    Right now the only mutable field is ``role``. Demoting the owner is
    refused at the API layer (must transfer first).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: MemberRole

    @field_validator("role", mode="before")
    @classmethod
    def _role_allowed(cls, v: object) -> str:
        return _coerce_role(v)


class MembershipRead(BaseModel):
    """Wire shape — includes joined ``user`` for one-shot rendering."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    user_id: int
    role: str
    invited_by: int | None = None
    joined_at: datetime | None = None
    user: UserPublic | None = None


class TransferOwnership(BaseModel):
    """``POST /organizations/{org_id}/transfer`` body.

    The acting user must currently be the owner. ``new_owner_id`` must be
    an existing admin or member of the same org.
    """

    model_config = ConfigDict(extra="forbid")

    new_owner_id: int = Field(gt=0)


__all__ = [
    "MemberRole",
    "MembershipBase",
    "MembershipCreate",
    "MembershipRead",
    "MembershipUpdate",
    "TransferOwnership",
]
