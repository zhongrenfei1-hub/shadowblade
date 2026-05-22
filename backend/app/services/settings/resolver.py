"""Settings resolver — auto-materialise, default-merge, integration hooks.

This module is the *single* place that knows how to:

1. Return a profile / org settings row, creating one with defaults if it
   doesn't exist yet (so endpoints never have to special-case the empty
   state).
2. Compute the *effective* brand kit / template / render-default tuple
   that the mix-video pipeline should use for a given (workspace, user)
   pair. The resolution order intentionally matches the brand-kit
   resolver so behaviour stays consistent: a user-scoped active kit
   wins over a workspace-scoped active kit wins over the org-settings
   ``default_brand_kit_id`` wins over None.
3. React to upstream events from the Brand Kit / Template modules so
   referential integrity is preserved without us having to add explicit
   foreign-key constraints to the JSON-friendly defaults.

Every public function is async and takes an :class:`AsyncSession` so
callers control transaction boundaries — we never commit on behalf of
the caller (except for the auto-materialise path, which has to so the
row id is stable across nested calls).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_kit import BrandKit as BrandKitORM
from app.models.settings import OrganizationSettings, UserProfileSettings
from app.schemas.settings import EffectiveRenderDefaults

log = logging.getLogger("shadowblade.services.settings")


# ---------------------------------------------------------------------------
# Auto-materialise helpers
# ---------------------------------------------------------------------------


async def get_or_create_profile_settings(
    db: AsyncSession,
    *,
    user_id: int,
) -> UserProfileSettings:
    """Return the ``UserProfileSettings`` row for ``user_id``, creating it
    on first read.

    Auto-create runs in the *caller's* session so the row is visible
    inside the same transaction without an explicit ``flush`` — but we
    still ``commit`` because the row needs a stable primary key before
    a subsequent ``PATCH`` writes back to it.
    """
    stmt = select(UserProfileSettings).where(
        UserProfileSettings.user_id == user_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is not None:
        return row

    row = UserProfileSettings(user_id=user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    log.info("profile-settings materialised user_id=%s", user_id)
    return row


async def get_or_create_org_settings(
    db: AsyncSession,
    *,
    workspace_id: int,
) -> OrganizationSettings:
    """Return the ``OrganizationSettings`` row for ``workspace_id``,
    materialising one with defaults on first read.
    """
    stmt = select(OrganizationSettings).where(
        OrganizationSettings.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is not None:
        return row

    row = OrganizationSettings(workspace_id=workspace_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    log.info("organization-settings materialised workspace_id=%s", workspace_id)
    return row


# ---------------------------------------------------------------------------
# Effective resolution
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _BrandKitMatch:
    """Tiny internal value object — kit id + resolution source.

    The mix-video pipeline doesn't care *where* the kit came from, but
    the diagnostics endpoint does, so we keep the source label around
    for future surfacing.
    """

    brand_kit_id: int | None
    source: str  # 'user' | 'workspace' | 'org_settings_default' | 'none'


async def _resolve_brand_kit(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int | None,
) -> _BrandKitMatch:
    """Apply the four-step resolution order.

    1. user-scoped active kit for this (workspace, user)
    2. workspace-scoped active kit
    3. ``organization_settings.default_brand_kit_id`` (and verify the row
       still exists + is_active; otherwise fall through)
    4. None — the caller will use the in-process ``default_kit()``
    """
    # 1. user-scoped
    if user_id is not None:
        stmt = (
            select(BrandKitORM.id)
            .where(
                BrandKitORM.workspace_id == workspace_id,
                BrandKitORM.scope == "user",
                BrandKitORM.owner_id == user_id,
                BrandKitORM.is_active.is_(True),
            )
            .order_by(BrandKitORM.id.desc())
            .limit(1)
        )
        match_id = (await db.execute(stmt)).scalar_one_or_none()
        if match_id is not None:
            return _BrandKitMatch(brand_kit_id=match_id, source="user")

    # 2. workspace-scoped
    stmt = (
        select(BrandKitORM.id)
        .where(
            BrandKitORM.workspace_id == workspace_id,
            BrandKitORM.scope == "workspace",
            BrandKitORM.is_active.is_(True),
        )
        .order_by(BrandKitORM.id.desc())
        .limit(1)
    )
    match_id = (await db.execute(stmt)).scalar_one_or_none()
    if match_id is not None:
        return _BrandKitMatch(brand_kit_id=match_id, source="workspace")

    # 3. org-settings default — verify the FK target is still active.
    org_stmt = select(OrganizationSettings.default_brand_kit_id).where(
        OrganizationSettings.workspace_id == workspace_id
    )
    org_default = (await db.execute(org_stmt)).scalar_one_or_none()
    if org_default is not None:
        verify_stmt = (
            select(BrandKitORM.id)
            .where(
                BrandKitORM.id == org_default,
                BrandKitORM.workspace_id == workspace_id,
                BrandKitORM.is_active.is_(True),
            )
            .limit(1)
        )
        match_id = (await db.execute(verify_stmt)).scalar_one_or_none()
        if match_id is not None:
            return _BrandKitMatch(
                brand_kit_id=match_id, source="org_settings_default"
            )

    return _BrandKitMatch(brand_kit_id=None, source="none")


async def resolve_effective_brand_kit_id(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int | None,
) -> int | None:
    """Public thin wrapper — return the int id (or ``None``)."""
    match = await _resolve_brand_kit(
        db, workspace_id=workspace_id, user_id=user_id
    )
    return match.brand_kit_id


async def resolve_render_defaults(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int | None,
) -> EffectiveRenderDefaults:
    """Compute the effective render defaults for a mix-video request.

    The mix-video endpoint folds these onto the request whenever the
    caller didn't explicitly set the corresponding field. We auto-
    materialise the org-settings row so the result is deterministic —
    even a brand-new workspace sees the documented defaults.
    """
    org = await get_or_create_org_settings(db, workspace_id=workspace_id)
    kit_match = await _resolve_brand_kit(
        db, workspace_id=workspace_id, user_id=user_id
    )

    return EffectiveRenderDefaults(
        workspace_id=workspace_id,
        user_id=user_id,
        brand_kit_id=kit_match.brand_kit_id,
        template_slug=org.default_template_slug,
        aspect_ratio=org.default_aspect_ratio,
        voice=org.default_voice,
        codec=org.default_codec,
        loudness_lufs=org.default_loudness_lufs,
        watermark_enabled=org.video_watermark_enabled,
        watermark_drafts_only=org.watermark_drafts_only,
        language=org.language,
        timezone=org.timezone,
    )


# ---------------------------------------------------------------------------
# Integration hooks
# ---------------------------------------------------------------------------


async def on_brand_kit_deleted(
    db: AsyncSession,
    *,
    workspace_id: int,
    brand_kit_id: int,
) -> int:
    """Clear ``default_brand_kit_id`` if it was pointing at the deleted kit.

    Returns the number of org-settings rows updated (0 or 1) — useful
    for logging and tests. The brand-kit DELETE endpoint calls this as
    its very last step.
    """
    stmt = (
        update(OrganizationSettings)
        .where(
            OrganizationSettings.workspace_id == workspace_id,
            OrganizationSettings.default_brand_kit_id == brand_kit_id,
        )
        .values(default_brand_kit_id=None)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    if result.rowcount:
        await db.commit()
        log.info(
            "org-settings default_brand_kit cleared workspace=%s brand_kit=%s",
            workspace_id,
            brand_kit_id,
        )
    return result.rowcount or 0


async def on_brand_kit_updated(
    db: AsyncSession,
    *,
    workspace_id: int,
    brand_kit_id: int,
    is_active: bool,
) -> int:
    """React to a brand kit being deactivated.

    When ``is_active=False``, behave like :func:`on_brand_kit_deleted` —
    we don't want the resolver picking a deactivated kit via the org
    default. When ``is_active=True`` we don't auto-attach (the user
    explicitly sets ``default_brand_kit_id`` through the org-settings
    PATCH endpoint).
    """
    if is_active:
        return 0
    return await on_brand_kit_deleted(
        db, workspace_id=workspace_id, brand_kit_id=brand_kit_id
    )


async def on_template_deleted(
    db: AsyncSession,
    *,
    workspace_id: int,
    template_slug: str,
) -> int:
    """Clear ``default_template_slug`` when the referenced template is
    removed. Called by the template service so the same referential-
    integrity contract holds for templates as for brand kits.
    """
    stmt = (
        update(OrganizationSettings)
        .where(
            OrganizationSettings.workspace_id == workspace_id,
            OrganizationSettings.default_template_slug == template_slug,
        )
        .values(default_template_slug=None)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(stmt)
    if result.rowcount:
        await db.commit()
        log.info(
            "org-settings default_template cleared workspace=%s template=%s",
            workspace_id,
            template_slug,
        )
    return result.rowcount or 0


__all__ = [
    "get_or_create_org_settings",
    "get_or_create_profile_settings",
    "on_brand_kit_deleted",
    "on_brand_kit_updated",
    "on_template_deleted",
    "resolve_effective_brand_kit_id",
    "resolve_render_defaults",
]
