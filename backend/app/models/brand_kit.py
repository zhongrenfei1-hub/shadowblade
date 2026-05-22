"""BrandKit ORM — workspace- or user-scoped brand identity bundle.

Stores the colours, fonts, voice, watermark policy, default template, and
custom CSS that downstream features (template framework, mix pipeline,
cover generation, subtitle styling) consume at render time.

Two scopes are supported:

* ``scope='workspace'`` — shared across the whole workspace; ``owner_id`` is
  ``NULL``. Exactly one such kit per workspace should be marked as
  *active* via the ``is_active`` flag.
* ``scope='user'``      — overrides the workspace default for one teammate;
  ``owner_id`` points at ``users.id``.

The mix-video pipeline always resolves the effective kit by:

    1. user-scoped active kit (if the request carries a user id)
    2. workspace-scoped active kit
    3. :func:`app.services.video.brand.default_kit` (process-wide fallback)

See :mod:`app.schemas.brand_kit` for the validation layer and
:mod:`app.api.brand_kits` for the REST endpoints that read/write this
table.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BrandKit(Base):
    __tablename__ = "brand_kits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- ownership ----------------------------------------------------------
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    # 'workspace' (org-wide default) or 'user' (per-member override).
    scope: Mapped[str] = mapped_column(String(16), default="workspace", index=True)
    # Populated only when scope='user'. Lets us run a user-scoped kit on top
    # of the workspace one.
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    # Exactly one active kit per (workspace_id, scope, owner_id) tuple is
    # expected — enforced at the API layer, not the DB, so we can support
    # historical/inactive kits without a unique constraint headache.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # --- identity -----------------------------------------------------------
    name: Mapped[str] = mapped_column(String(255))

    # --- palette (validated as hex at the schema layer) ---------------------
    primary_color: Mapped[str] = mapped_column(String(9), default="#0F2A4A")
    secondary_color: Mapped[str] = mapped_column(String(9), default="#F5F7FB")
    accent_color: Mapped[str] = mapped_column(String(9), default="#22D3B7")
    neutral_color: Mapped[str] = mapped_column(String(9), default="#5A6B85")
    background_color: Mapped[str] = mapped_column(String(9), default="#FFFFFF")

    # --- typography ---------------------------------------------------------
    font_family: Mapped[str] = mapped_column(String(128), default="Inter")
    font_heading: Mapped[str] = mapped_column(String(128), default="Inter")
    font_body: Mapped[str] = mapped_column(String(128), default="Inter")

    # --- assets -------------------------------------------------------------
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    logo_mono_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    intro_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    outro_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # --- watermark policy ---------------------------------------------------
    watermark_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    watermark_opacity: Mapped[float] = mapped_column(Float, default=0.78)
    watermark_position: Mapped[str] = mapped_column(String(8), default="br")
    watermark_width_pct: Mapped[float] = mapped_column(Float, default=0.16)

    # --- audio bus knobs ----------------------------------------------------
    voice: Mapped[str] = mapped_column(String(64), default="alloy-en-female")
    target_lufs: Mapped[float] = mapped_column(Float, default=-14.0)
    target_tp: Mapped[float] = mapped_column(Float, default=-1.0)
    bgm_gain_db: Mapped[float] = mapped_column(Float, default=-14.0)

    # --- subtitle baseline --------------------------------------------------
    subtitle_size: Mapped[int] = mapped_column(Integer, default=64)
    subtitle_margin_v: Mapped[int] = mapped_column(Integer, default=96)

    # --- defaults the user gets in mix-video --------------------------------
    default_template_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    custom_css_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- editorial tone (free-form) -----------------------------------------
    tone: Mapped[dict] = mapped_column(JSON, default=dict)

    # --- timestamps ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = ["BrandKit"]
