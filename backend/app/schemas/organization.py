"""Organization (a.k.a. Workspace) — Pydantic V2 schemas.

The underlying storage is the legacy :class:`app.models.workspace.Workspace`
table, so every back-end field carries through unchanged. The schemas
here are the contract for ``/api/v1/organizations`` — phrased in
"organization" vocabulary because that's what the UI surfaces.

Slug rules (matched against ``OrganizationCreate.slug``):

* 2–48 chars
* lowercase ascii letters, digits, hyphens
* must start with a letter
* no consecutive hyphens
* may not end with a hyphen

This is stricter than the loose ``String(64)`` in the ORM on purpose —
once a slug is in the URL we don't want to spend energy escaping it.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def validate_slug(value: str) -> str:
    """Lower-case the slug, then validate against the production rules.

    Raises
    ------
    ValueError
        If the slug violates length, charset, or shape rules.
    """
    v = value.strip().lower()
    if not (2 <= len(v) <= 48):
        raise ValueError("slug must be 2–48 characters")
    if not _SLUG_RE.match(v):
        raise ValueError(
            "slug must start with a letter and contain only lowercase letters, "
            "digits, and single hyphens between non-empty segments"
        )
    return v


SlugStr = Annotated[
    str,
    Field(
        min_length=2,
        max_length=48,
        description="URL-safe slug; lowercase, alnum, hyphens.",
    ),
]


# ---------------------------------------------------------------------------
# Base / Create / Update / Read
# ---------------------------------------------------------------------------


class OrganizationBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=512)


class OrganizationCreate(OrganizationBase):
    """``POST /organizations`` body.

    The slug is required because the URL surface (``/orgs/<slug>``) is a
    user-facing artefact that should be picked deliberately, not derived
    from the display name and silently disambiguated.
    """

    slug: SlugStr
    # Plan/seats default to the demo values; admin-elevated routes can
    # change them later. Kept here so the test-fixture path doesn't have
    # to PATCH them in.
    plan: str = Field(default="growth", max_length=32)
    seats: int = Field(default=5, ge=1, le=10_000)
    monthly_render_quota: int = Field(default=200, ge=0, le=1_000_000)

    @field_validator("slug", mode="before")
    @classmethod
    def _normalise_slug(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError("slug must be a string")
        return validate_slug(v)


class OrganizationUpdate(BaseModel):
    """``PATCH /organizations/{org_id}`` body — all fields optional."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=512)
    plan: str | None = Field(default=None, max_length=32)
    seats: int | None = Field(default=None, ge=1, le=10_000)
    monthly_render_quota: int | None = Field(default=None, ge=0, le=1_000_000)
    # slug rename is allowed but routed through a dedicated endpoint in
    # the API layer; leaving it out here prevents accidental rewrites.


class OrganizationRead(BaseModel):
    """Wire shape for read responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None = None
    avatar_url: str | None = None
    owner_id: int | None = None
    plan: str = "growth"
    seats: int = 5
    monthly_render_quota: int = 200
    monthly_render_used: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Decorated by the API layer when the request is in a member's context.
    role: str | None = None  # caller's role inside this org, if known
    member_count: int | None = None  # filled when listed via /organizations


class OrganizationSummary(BaseModel):
    """Compact form for sidebars / org-switchers."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    avatar_url: str | None = None
    role: str | None = None


__all__ = [
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationRead",
    "OrganizationSummary",
    "OrganizationUpdate",
    "SlugStr",
    "validate_slug",
]
