"""Notification ORM — workspace inbox events.

Models the rows surfaced by ``GET /api/v1/notifications`` and the
frontend's *Workspace · Inbox* page. One row = one event delivered to
one user inside one workspace; broadcast/announcement-style events are
fanned out at write-time so reads stay a single indexed query.

Field design tracks two existing shapes:

* The current React mock in
  ``frontend-next/app/(app)/notifications/page.tsx`` — six tab buckets
  (``all``/``approvals``/``mentions``/``pipeline``/``drift``/``billing``)
  and six visual kinds (``done``/``mention``/``info``/``warn``/``fail``/
  ``billing``).
* The fastapi-fullstack-template *user-inbox* convention — per-user
  rows, ``read`` boolean, ``payload`` JSON for type-specific extras.

The ``category`` field is the tab bucket; ``kind`` is the visual
severity. We keep them separate columns (rather than deriving one from
the other) because the mapping is many-to-many in practice: a *pipeline*
event can be ``done``, ``info``, or ``fail`` depending on how the render
ended, and a *mention* event is always ``mention`` regardless of tab.

Indexes cover the three hot read patterns: list-by-user, count-unread,
and filter-by-category. ``workspace_id`` is denormalised onto the row so
permission checks never have to JOIN through ``users``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# --- enum-style string constants -------------------------------------------
#
# We keep these as plain strings (not Python enums) because:
#   * SQLAlchemy String columns round-trip JSON cleanly without a dialect-
#     specific ENUM type;
#   * the React mock uses bare strings (``"done"``, ``"approvals"``);
#   * the Pydantic schema layer enforces the closed set via ``Literal[...]``
#     so we still get validation at the API boundary.

NOTIFICATION_TYPES: tuple[str, ...] = (
    "video_generated",      # mix-video render finished (success)
    "video_failed",         # mix-video render failed
    "template_updated",     # someone edited a template the workspace uses
    "template_published",   # new template published into the workspace
    "team_invite",          # new teammate invited / joined
    "team_member_joined",   # invite was accepted
    "brand_kit_changed",    # workspace brand kit was updated
    "brand_drift_detected", # render used colors/fonts off the active kit
    "mention",              # someone @-mentioned the user
    "approval_requested",   # producer asked reviewer to sign off
    "approval_granted",     # reviewer approved
    "billing",              # quota / billing notice
    "system",               # generic system notice
)

# Tab bucket the frontend uses to filter the inbox. Map: type → category.
NOTIFICATION_CATEGORIES: tuple[str, ...] = (
    "pipeline",   # video_generated / video_failed / template_*
    "approvals",  # approval_requested / approval_granted
    "mentions",   # mention
    "drift",      # brand_kit_changed / brand_drift_detected
    "billing",    # billing
    "system",     # team_invite / team_member_joined / system
)

# Visual severity the frontend uses to pick the icon/color.
NOTIFICATION_KINDS: tuple[str, ...] = (
    "done",      # success
    "mention",   # @-mention
    "info",      # neutral info
    "warn",      # warning (e.g. brand drift)
    "fail",      # error / failure
    "billing",   # billing-flavoured
)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- delivery target ----------------------------------------------------
    # ``user_id`` is NULL only when the row is a workspace-wide broadcast
    # nobody has personally subscribed to yet — in practice we fan out on
    # write so this stays non-NULL for normal flows.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), nullable=False, index=True
    )

    # --- classification -----------------------------------------------------
    type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="info")

    # --- content ------------------------------------------------------------
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # --- type-specific extras (video_id, template_name, actor_id, ...) ------
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # --- state --------------------------------------------------------------
    read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    # --- timestamps ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        # The two list endpoints hit (user_id, read, created_at) and
        # (workspace_id, category, created_at). Cover both with composite
        # indexes so SQLite + Postgres serve them without a sort step.
        Index(
            "ix_notifications_user_unread_created",
            "user_id",
            "read",
            "created_at",
        ),
        Index(
            "ix_notifications_workspace_category_created",
            "workspace_id",
            "category",
            "created_at",
        ),
    )


__all__ = [
    "NOTIFICATION_CATEGORIES",
    "NOTIFICATION_KINDS",
    "NOTIFICATION_TYPES",
    "Notification",
]
