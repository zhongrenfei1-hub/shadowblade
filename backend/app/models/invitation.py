"""WorkspaceInvite ORM — pending email invitations to join an org.

Lifecycle:

    pending ──accept──▶ accepted   (links to the WorkspaceMember row)
        │
        ├──revoke──▶ revoked
        └──expire──▶ expired       (set on read when ``expires_at < now``)

The ``invite_code`` is the secret token shared in the invitation email; it
is unique and indexed because the public ``/invitations/{code}/accept``
endpoint looks invites up by code. We generate codes with
``secrets.token_urlsafe(24)`` (32 chars, URL-safe, 192 bits of entropy) —
enough to be unguessable.

Multiple pending invites for the same ``(workspace_id, email)`` pair are
*allowed* — admins can re-send an invite by creating a new one, and the
revoke flow will tag the previous one. The accept endpoint always picks
the latest non-expired pending row.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class WorkspaceInvite(Base):
    __tablename__ = "workspace_invites"
    __table_args__ = (
        # Speed up the "list invites by workspace" admin view and the
        # "find latest pending for email+ws" path used by /accept.
        Index(
            "ix_workspace_invites_ws_status",
            "workspace_id",
            "status",
        ),
        Index(
            "ix_workspace_invites_email_status",
            "email",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)

    # Secret token shared with the invitee. 32 URL-safe chars by default.
    invite_code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    invited_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # pending | accepted | revoked | expired
    status: Mapped[str] = mapped_column(
        String(16), default="pending", index=True, nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # --- relationships ------------------------------------------------------
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        back_populates="invitations",
    )
    inviter: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[invited_by],
        lazy="joined",
    )
    acceptor: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[accepted_by],
        lazy="joined",
    )


__all__ = ["WorkspaceInvite"]
