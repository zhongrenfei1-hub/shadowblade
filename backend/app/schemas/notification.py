"""Notification — Pydantic V2 schemas.

Wire shapes for ``/api/v1/notifications/*``. Layout mirrors the
fastapi-fullstack-template convention so the React notifications page
can predict every endpoint's response without reading the OpenAPI doc:

* ``NotificationBase``   — fields shared by Create / Read.
* ``NotificationCreate`` — body for the (internal) create call invoked
  by the service layer + tests; not exposed as a public REST route.
* ``NotificationRead``   — wire shape for GET responses.
* ``NotificationList``   — paginated envelope returned by ``GET /``.
* ``UnreadCountResponse``— body of ``GET /unread-count``.

Validation rules:
    * ``type`` / ``category`` / ``kind`` are ``Literal`` over the closed
      enums declared in :mod:`app.models.notification`; sending anything
      else is a 422.
    * ``title`` is trimmed and length-bounded so the frontend never has
      to truncate.
    * ``payload`` is an open ``dict`` — the per-type contract lives in
      :mod:`app.services.notifications` (see the ``notify_*`` helpers).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import (
    NOTIFICATION_CATEGORIES,
    NOTIFICATION_KINDS,
    NOTIFICATION_TYPES,
)

# ``Literal`` doesn't accept a runtime tuple in plain annotation form, so
# we synthesise the types via ``Literal.__getitem__`` at module import.
# Keeps the enum lists in app.models the single source of truth.
NotificationType = Literal[NOTIFICATION_TYPES]  # type: ignore[valid-type]
NotificationCategory = Literal[NOTIFICATION_CATEGORIES]  # type: ignore[valid-type]
NotificationKind = Literal[NOTIFICATION_KINDS]  # type: ignore[valid-type]


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------


class NotificationBase(BaseModel):
    """Fields shared by Create and Read shapes."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    type: NotificationType
    category: NotificationCategory
    kind: NotificationKind = "info"
    title: Annotated[str, Field(min_length=1, max_length=255)]
    message: str = Field(default="", max_length=4000)
    payload: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class NotificationCreate(NotificationBase):
    """Internal write shape — never bound to a public POST endpoint.

    The service layer (and tests) use this to keep type/category/kind
    validation in one place. Public traffic creates rows indirectly via
    the trigger hooks in mix-video, brand_kits, templates, etc.
    """

    user_id: int | None = Field(default=None, ge=1)
    workspace_id: int = Field(ge=1)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class NotificationRead(NotificationBase):
    """Wire shape for GET responses."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )

    id: int
    user_id: int | None = None
    workspace_id: int
    read: bool = False
    read_at: datetime | None = None
    archived: bool = False
    created_at: datetime


class NotificationList(BaseModel):
    """Paginated envelope returned by ``GET /notifications``."""

    items: list[NotificationRead]
    total: int = Field(ge=0)
    unread: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class UnreadCountResponse(BaseModel):
    """Body of ``GET /notifications/unread-count``."""

    unread: int = Field(ge=0)


class MarkResponse(BaseModel):
    """Returned by mark-read / mark-all-read endpoints."""

    ok: bool = True
    updated: int = Field(ge=0)


__all__ = [
    "MarkResponse",
    "NotificationBase",
    "NotificationCategory",
    "NotificationCreate",
    "NotificationKind",
    "NotificationList",
    "NotificationRead",
    "NotificationType",
    "UnreadCountResponse",
]
