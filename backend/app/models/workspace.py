"""Workspace ORM — the underlying storage for Team/Organization entities.

The ``Workspace`` table is the single source of truth for both the legacy
``/workspaces/me`` endpoint and the newer ``/organizations`` REST family.
We keep the table name ``workspaces`` (and the existing column set) so that
every downstream model — ``Project``, ``Asset``, ``BrandKit`` — keeps its
foreign key intact. New columns are nullable for backward compatibility:

* ``owner_id``     points at the user who created the org. ``NULL`` is
  tolerated for the demo workspace materialised on first boot before any
  real user has registered.
* ``description``  free-form team description shown in the UI header.
* ``avatar_url``   square brand mark URL for the team switcher.
* ``updated_at``   bumped on every PATCH (used for caching).

The membership and invitation entities live in separate tables — see
:mod:`app.models.membership` and :mod:`app.models.invitation`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))

    # --- ownership ----------------------------------------------------------
    # Nullable so the demo workspace (id=1) survives even when no user has
    # registered yet. New orgs created through /organizations always have a
    # non-null owner_id.
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # --- presentation -------------------------------------------------------
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # --- billing / capacity (unchanged) ------------------------------------
    plan: Mapped[str] = mapped_column(String(32), default="growth")
    seats: Mapped[int] = mapped_column(Integer, default=5)
    monthly_render_quota: Mapped[int] = mapped_column(Integer, default=200)
    monthly_render_used: Mapped[int] = mapped_column(Integer, default=0)

    # --- timestamps ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # --- relationships ------------------------------------------------------
    members: Mapped[list["WorkspaceMember"]] = relationship(  # noqa: F821
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    invitations: Mapped[list["WorkspaceInvite"]] = relationship(  # noqa: F821
        "WorkspaceInvite",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


__all__ = ["Workspace"]
