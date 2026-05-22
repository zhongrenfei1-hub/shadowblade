"""Settings ORM — three-scope configuration store.

Provides the persistence layer for the ``/api/v1/settings/*`` REST family.
Three independent entities share this module:

* :class:`UserProfileSettings` — one row per :class:`~app.models.user.User`.
  Holds the *personal* preferences that follow a user across workspaces:
  display nickname, locale, time zone, theme, and notification opt-ins.
  Distinct from the :class:`~app.models.user.User` row itself so a future
  identity provider can own ``email`` / ``full_name`` while the user keeps
  control of their UX preferences.

* :class:`OrganizationSettings` — one row per
  :class:`~app.models.workspace.Workspace`. Holds the workspace-wide
  *defaults* that the mix-video pipeline, render queue, and brand-drift
  detector consume at run time: default brand kit, default template,
  watermark policy, loudness target, security posture, notification
  routing. The row's ``workspace_id`` is the primary key — exactly one
  row exists per workspace, materialised lazily on first read.

* :class:`AppSetting` — global key/value store for cross-cutting feature
  flags and operational knobs (e.g. ``ai.generation_enabled``,
  ``mix.max_concurrent_renders``). Kept intentionally schemaless so
  shipping a new flag is an INSERT, not a migration.

The three tables are deliberately *separate* (rather than one polymorphic
``settings`` table with a ``scope`` column) because the cardinality and
ownership rules differ enough that a single table would force every read
to filter on a discriminator. Splitting them keeps the indexes tight and
the type signatures honest.

See:
* :mod:`app.schemas.settings`   — validation layer
* :mod:`app.services.settings`  — resolver / auto-materialise helpers
* :mod:`app.api.settings`       — REST endpoints
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


class UserProfileSettings(Base):
    """Per-user preferences row.

    The primary key is also a foreign key to ``users.id`` because there is
    at most one settings row per user. ``ondelete='CASCADE'`` keeps the
    settings row in lock-step with account deletion.
    """

    __tablename__ = "user_profile_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # --- presentation -------------------------------------------------------
    # Optional override for the avatar URL stored on ``users.avatar_url``.
    # NULL means "fall back to the User row" — most callers should resolve
    # via :func:`app.services.settings.resolver.effective_user_profile`.
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- locale -------------------------------------------------------------
    # IETF BCP 47 tag, e.g. "zh-CN" / "en-US" / "ja-JP". The frontend uses
    # this to pick a translation bundle and number/date formats.
    language: Mapped[str] = mapped_column(String(16), default="zh-CN", nullable=False)
    # IANA tz database name, e.g. "Asia/Shanghai" / "UTC" / "America/New_York".
    timezone: Mapped[str] = mapped_column(
        String(48), default="Asia/Shanghai", nullable=False
    )
    # "iso" → 2026-05-22, "us" → 05/22/2026, "eu" → 22/05/2026.
    date_format: Mapped[str] = mapped_column(String(8), default="iso", nullable=False)

    # --- theme --------------------------------------------------------------
    # "system" → follow OS, "light" / "dark" → explicit choice.
    theme: Mapped[str] = mapped_column(String(8), default="system", nullable=False)

    # --- notification opt-ins ----------------------------------------------
    # Top-level kill switch for all email channels.
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # Browser desktop push (where supported).
    desktop_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # Distinct from email so a user can disable email but keep in-app pings.
    mention_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # Periodic digest mode for the inbox: "off" / "daily" / "weekly".
    inbox_digest: Mapped[str] = mapped_column(
        String(8), default="weekly", nullable=False
    )
    # Soft UI affordance — small sound on new notifications.
    sound_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # --- workspace landing --------------------------------------------------
    # Optional default workspace the UI redirects to after login. NULL means
    # "use the most-recently-active workspace".
    default_workspace_id: Mapped[int | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- editor ergonomics --------------------------------------------------
    keyboard_shortcuts_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    autosave_drafts: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

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


class OrganizationSettings(Base):
    """Per-workspace defaults row.

    The ``workspace_id`` is also the primary key — exactly one row per
    workspace. The row is *auto-materialised* on first read by
    :func:`app.services.settings.resolver.get_or_create_org_settings` so
    every workspace appears to "already have" defaults from day one.

    The settings here are the single source of truth for:

    * mix-video pipeline defaults (loudness, codec, watermark policy)
    * UI defaults (region label, timezone, public preview toggle)
    * security posture (session length, MFA enforcement, IP allowlist)
    * notification routing (which categories to forward to Slack, etc.)

    ``default_brand_kit_id`` and ``default_template_slug`` are the
    integration anchors: brand-kit deletion clears the first, and
    template renames update the second.
    """

    __tablename__ = "organization_settings"

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # --- workspace identity overrides --------------------------------------
    # Display name override — fall back to ``workspaces.name`` when NULL.
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # ``region`` is presentation only; actual data residency is operational.
    region: Mapped[str] = mapped_column(
        String(32), default="eu-central-1", nullable=False
    )
    # Org-wide default timezone for KPIs / cron / digests.
    timezone: Mapped[str] = mapped_column(
        String(48), default="UTC", nullable=False
    )
    # Org-wide default UI language for new members.
    language: Mapped[str] = mapped_column(
        String(16), default="zh-CN", nullable=False
    )

    # --- creative defaults --------------------------------------------------
    # The brand kit fed to mix-video when the caller doesn't have a user-
    # scoped kit. ``ON DELETE SET NULL`` so deleting a kit doesn't 500 us.
    default_brand_kit_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand_kits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Template slug fed into mix-video / generate when the caller omits one.
    # Stored as a string (not FK) because templates live both in the DB and
    # in JSON files under ``templates/``.
    default_template_slug: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    default_aspect_ratio: Mapped[str] = mapped_column(
        String(8), default="9:16", nullable=False
    )
    default_voice: Mapped[str] = mapped_column(
        String(64), default="alloy-en-female", nullable=False
    )

    # --- render policy ------------------------------------------------------
    # "h264" | "h265" | "prores_422_hq".
    default_codec: Mapped[str] = mapped_column(
        String(16), default="h264", nullable=False
    )
    # LUFS target; mirrors brand_kit.target_lufs default range.
    default_loudness_lufs: Mapped[float] = mapped_column(
        Float, default=-14.0, nullable=False
    )
    # Master switch: when False, mix-video skips any watermark step
    # regardless of what the brand kit says.
    video_watermark_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # When True, only drafts (preview / non-approved) get a watermark.
    watermark_drafts_only: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Kick the render queue automatically once a project is approved.
    auto_render_on_approval: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # Whether ``/preview`` links can be shared publicly (read-only).
    public_preview_links_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # --- security posture ---------------------------------------------------
    sso_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    force_mfa: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    session_duration_hours: Mapped[int] = mapped_column(
        Integer, default=12, nullable=False
    )
    ip_allowlist_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # JSON list of CIDR strings; empty list = no restriction.
    ip_allowlist: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # --- notification routing ----------------------------------------------
    # Per-category dict: ``{"approvals": True, "drift": False, ...}``.
    # Keys MUST be a subset of ``app.models.notification.NOTIFICATION_CATEGORIES``.
    # An empty dict means "fall back to per-user preferences".
    notification_preferences: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    # Trigger ``brand_drift_detected`` notifications when a render diverges
    # from the active kit. Off by default to avoid noisy dev installs.
    brand_drift_warning_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # --- data & export ------------------------------------------------------
    # JSON list of allowed formats, e.g. ["mp4", "mov", "webm"].
    allowed_export_formats: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    # Soft retention for renders (days). 0 = unlimited. UI surfaces this.
    retention_days: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

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


class AppSetting(Base):
    """Cross-cutting global key/value setting.

    Use cases:

    * Feature flags (e.g. ``feature.beta_studio_enabled = true``)
    * Operational knobs (e.g. ``render.max_concurrent = 8``)
    * Public marketing copy (e.g. ``marketing.hero_caption = "Ship..."``)

    Reads are cheap (single PK lookup), writes are admin-only at the API
    layer. ``is_public=True`` exposes the key to unauthenticated reads —
    used for marketing copy and feature-flag introspection from the UI.
    """

    __tablename__ = "app_settings"

    # Dotted-path key, e.g. ``"render.max_concurrent"``.
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    # Arbitrary JSON value; the schema layer validates per-key shape.
    value: Mapped[object] = mapped_column(JSON, nullable=False)
    # Optional human-readable description for the admin UI.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When True, non-admin / unauthenticated readers can fetch this key.
    is_public: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    # Audit: who last wrote this row (NULL = system / migration).
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = [
    "AppSetting",
    "OrganizationSettings",
    "UserProfileSettings",
]
