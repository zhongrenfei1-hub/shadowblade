"""User — Pydantic V2 schemas for the auth + Team APIs.

Layered the same way as :mod:`app.schemas.brand_kit` so frontend can rely
on a predictable shape:

* ``UserBase``    — fields shared by request and response.
* ``UserCreate``  — body of ``POST /auth/register`` (validates password +
  optional username).
* ``UserUpdate``  — body of ``PATCH /users/me`` (every field optional).
* ``UserRead``    — wire shape returned to the client (never includes the
  password hash).
* ``UserPublic``  — ultra-stripped view for member lists (no email).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Password rules — defence in depth alongside the bcrypt 72-byte cap.
PasswordStr = Annotated[
    str,
    Field(
        min_length=8,
        max_length=72,
        description="8–72 chars. UTF-8 bytes also capped at 72 by bcrypt.",
    ),
]

# Username rules. Lowercase letters, digits, ``_`` and ``.`` — matches the
# handle conventions used by GitHub-style products. The leading-char rule
# (must start with a letter) keeps usernames out of the "looks like an id"
# bucket which avoids URL ambiguity later.
_USERNAME_RE = re.compile(r"^[a-z][a-z0-9_.]{2,47}$")


def validate_username(value: str) -> str:
    """Normalise and validate a username string.

    Returns the lower-cased form. Raises ``ValueError`` on any rule
    violation — caller-friendly messages so the 422 surface is useful.
    """
    v = value.strip().lower()
    if not v:
        raise ValueError("username cannot be empty")
    if len(v) < 3:
        raise ValueError("username must be at least 3 characters")
    if len(v) > 48:
        raise ValueError("username must be at most 48 characters")
    if not _USERNAME_RE.match(v):
        raise ValueError(
            "username must start with a letter and contain only "
            "lowercase letters, digits, '_' or '.'"
        )
    # Don't allow leading/trailing dots — those break some URL routing.
    if v.startswith(".") or v.endswith("."):
        raise ValueError("username may not start or end with '.'")
    if ".." in v:
        raise ValueError("username may not contain consecutive dots")
    return v


UsernameStr = Annotated[
    str,
    Field(
        min_length=3,
        max_length=48,
        description=(
            "3–48 chars, must start with a letter; lowercase, digits, "
            "'_' or '.'; no consecutive or trailing dots."
        ),
    ),
]


class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)


class UserCreate(UserBase):
    """Body shape of ``POST /auth/register``.

    A successful registration also creates a personal workspace for the
    user (handled in the API layer, not the schema).

    ``username`` is optional — if omitted, the API derives it from the
    email's local part. Explicit values are validated against the
    canonical handle rules in :func:`validate_username`.
    """

    password: PasswordStr
    username: UsernameStr | None = None

    @field_validator("password")
    @classmethod
    def _password_byte_cap(cls, v: str) -> str:
        # max_length is in *characters*; bcrypt cares about *bytes*.
        # Reject non-ASCII passwords that would exceed 72 bytes early so
        # the user gets a clear error rather than a hash-time crash.
        if len(v.encode("utf-8")) > 72:
            raise ValueError(
                "password exceeds 72 bytes when UTF-8 encoded; "
                "use a shorter password"
            )
        return v

    @field_validator("username", mode="before")
    @classmethod
    def _normalise_username(cls, v: object) -> object:
        # None means "derive from email" — let the API layer handle it.
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("username must be a string")
        return validate_username(v)


class UserUpdate(BaseModel):
    """PATCH-style update — every field optional.

    Email/password rotation is intentionally *not* in here; those go
    through dedicated endpoints (``/auth/change-password`` etc.) to keep
    the audit trail clean. Username rotation goes through ``PATCH
    /users/me/username`` (TODO — not yet shipped).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)


class UserRead(BaseModel):
    """Wire shape — never includes ``hashed_password``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str | None = None
    full_name: str
    role: str = "member"  # legacy system role; not org-scoped
    avatar_url: str | None = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    last_password_change_at: datetime | None = None
    email_verified_at: datetime | None = None


class UserPublic(BaseModel):
    """Minimal view for member-list responses (no email, no flags)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None = None
    full_name: str
    avatar_url: str | None = None


__all__ = [
    "PasswordStr",
    "UserBase",
    "UserCreate",
    "UserPublic",
    "UserRead",
    "UserUpdate",
    "UsernameStr",
    "validate_username",
]
