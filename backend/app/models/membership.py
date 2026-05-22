"""WorkspaceMember ORM — the user ⇄ organization relationship.

A row in this table grants a single ``User`` access to a single
``Workspace`` with one of four roles. The unique ``(workspace_id, user_id)``
constraint prevents accidental duplicate memberships at the DB layer.

Roles (in descending power, see :mod:`app.core.permissions`):

* ``owner``  – exactly one per org; can transfer/delete the org.
* ``admin``  – manage members, invites, brand kit; cannot delete org.
* ``member`` – create projects, render videos, edit assets.
* ``guest``  – read-only access to projects they were explicitly invited to.

The row also records *who* invited the member (``invited_by``) to support
audit trails. ``joined_at`` differs from ``created_at`` only when a row is
back-filled — invitations create the row at acceptance time.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # owner | admin | member | guest — enforced by app.core.permissions
    role: Mapped[str] = mapped_column(String(16), default="member", index=True)

    # Optional: who created this membership row (a current admin/owner, or
    # NULL if the user created their own org through registration).
    invited_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # --- relationships ------------------------------------------------------
    workspace: Mapped["Workspace"] = relationship(  # noqa: F821
        "Workspace",
        back_populates="members",
        foreign_keys=[workspace_id],
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[user_id],
        lazy="joined",
    )
    inviter: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[invited_by],
        lazy="joined",
    )


__all__ = ["WorkspaceMember"]
