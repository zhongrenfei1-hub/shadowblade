"""REST endpoints for the Settings module.

Three URL families share a single :class:`APIRouter` rooted at
``/api/v1/settings``:

* Profile (per-user) ------------------------------------------------------
    - ``GET    /api/v1/settings/profile``       — own profile prefs
    - ``PUT    /api/v1/settings/profile``       — PATCH-style update

* Organization (per-workspace) -------------------------------------------
    - ``GET    /api/v1/settings/organization``  — current workspace defaults
    - ``PUT    /api/v1/settings/organization``  — admin-gated PATCH update

* Aggregate / effective --------------------------------------------------
    - ``GET    /api/v1/settings``               — bundle (profile + org + effective)
    - ``GET    /api/v1/settings/effective``     — resolved render defaults

* App settings (global K/V, admin-managed) -------------------------------
    - ``GET    /api/v1/settings/app``           — list public-readable keys
    - ``GET    /api/v1/settings/app/{key}``     — read one key (public reads only)
    - ``POST   /api/v1/settings/app``           — create (admin)
    - ``PUT    /api/v1/settings/app/{key}``     — update (admin)
    - ``DELETE /api/v1/settings/app/{key}``     — delete (admin)

Permission model (header-driven via :func:`require_workspace_role`):

* Reads on profile/org/effective: open to any caller (mirrors brand-kit).
* PUT on profile: requires ``X-User-Id`` (you can only edit your own).
* PUT on organization: requires role ≥ admin in the current workspace.
* App-settings writes: require role ≥ admin (org-wide admin doubles as
  global admin until we ship a distinct super-admin role).

The router carries no global prefix — :mod:`app.main` mounts it under
``/api/v1`` to match every other API module.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user_id,
    get_current_workspace_id,
    get_db,
    require_workspace_role,
)
from app.models.brand_kit import BrandKit as BrandKitORM
from app.models.settings import (
    AppSetting,
    OrganizationSettings,
    UserProfileSettings,
)
from app.schemas.settings import (
    AppSettingCreate,
    AppSettingRead,
    AppSettingUpdate,
    EffectiveRenderDefaults,
    OrganizationSettingsRead,
    OrganizationSettingsUpdate,
    SettingsBundle,
    UserProfileSettingsRead,
    UserProfileSettingsUpdate,
)
from app.services.settings import (
    get_or_create_org_settings,
    get_or_create_profile_settings,
    resolve_render_defaults,
)

log = logging.getLogger("shadowblade.api.settings")
router = APIRouter(prefix="/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Internal serializers
# ---------------------------------------------------------------------------


def _isoformat(value: datetime | None) -> str | None:
    """ORM ``datetime`` → ISO string for the JSON response."""
    return value.isoformat() if value is not None else None


def _serialize_profile(row: UserProfileSettings) -> dict[str, Any]:
    return {
        "user_id": row.user_id,
        "nickname": row.nickname,
        "avatar_url": row.avatar_url,
        "bio": row.bio,
        "language": row.language,
        "timezone": row.timezone,
        "date_format": row.date_format,
        "theme": row.theme,
        "email_notifications_enabled": row.email_notifications_enabled,
        "desktop_notifications_enabled": row.desktop_notifications_enabled,
        "mention_notifications_enabled": row.mention_notifications_enabled,
        "inbox_digest": row.inbox_digest,
        "sound_enabled": row.sound_enabled,
        "default_workspace_id": row.default_workspace_id,
        "keyboard_shortcuts_enabled": row.keyboard_shortcuts_enabled,
        "autosave_drafts": row.autosave_drafts,
        "created_at": _isoformat(row.created_at),
        "updated_at": _isoformat(row.updated_at),
    }


def _serialize_org(row: OrganizationSettings) -> dict[str, Any]:
    return {
        "workspace_id": row.workspace_id,
        "display_name": row.display_name,
        "region": row.region,
        "timezone": row.timezone,
        "language": row.language,
        "default_brand_kit_id": row.default_brand_kit_id,
        "default_template_slug": row.default_template_slug,
        "default_aspect_ratio": row.default_aspect_ratio,
        "default_voice": row.default_voice,
        "default_codec": row.default_codec,
        "default_loudness_lufs": row.default_loudness_lufs,
        "video_watermark_enabled": row.video_watermark_enabled,
        "watermark_drafts_only": row.watermark_drafts_only,
        "auto_render_on_approval": row.auto_render_on_approval,
        "public_preview_links_enabled": row.public_preview_links_enabled,
        "sso_provider": row.sso_provider,
        "force_mfa": row.force_mfa,
        "session_duration_hours": row.session_duration_hours,
        "ip_allowlist_enabled": row.ip_allowlist_enabled,
        "ip_allowlist": list(row.ip_allowlist or []),
        "notification_preferences": dict(row.notification_preferences or {}),
        "brand_drift_warning_enabled": row.brand_drift_warning_enabled,
        "allowed_export_formats": list(row.allowed_export_formats or []),
        "retention_days": row.retention_days,
        "created_at": _isoformat(row.created_at),
        "updated_at": _isoformat(row.updated_at),
    }


def _serialize_app_setting(row: AppSetting) -> dict[str, Any]:
    return {
        "key": row.key,
        "value": row.value,
        "description": row.description,
        "is_public": row.is_public,
        "updated_by": row.updated_by,
        "created_at": _isoformat(row.created_at),
        "updated_at": _isoformat(row.updated_at),
    }


async def _verify_brand_kit_belongs(
    db: AsyncSession, *, workspace_id: int, brand_kit_id: int
) -> None:
    """Enforce the foreign-ish constraint on ``default_brand_kit_id``.

    SQLite's ``ON DELETE SET NULL`` only fires when the kit row is
    deleted, not when a caller PATCHes an org-settings row with a
    cross-workspace id. We validate here to keep the data clean.
    """
    stmt = select(BrandKitORM.id).where(
        BrandKitORM.id == brand_kit_id,
        BrandKitORM.workspace_id == workspace_id,
    )
    if (await db.execute(stmt)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"brand_kit_id {brand_kit_id} does not exist in workspace "
                f"{workspace_id}"
            ),
        )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/profile", response_model=UserProfileSettingsRead)
async def get_profile_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Return the caller's profile settings, materialising on first read.

    Anonymous callers get a 401 — profile settings are inherently user-
    scoped and have no meaningful workspace fallback.
    """
    if user_id is None:
        raise HTTPException(status_code=401, detail="user authentication required")
    row = await get_or_create_profile_settings(db, user_id=user_id)
    return _serialize_profile(row)


@router.put("/profile", response_model=UserProfileSettingsRead)
async def update_profile_settings(
    payload: UserProfileSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """PATCH-style update of the caller's own profile settings."""
    if user_id is None:
        raise HTTPException(status_code=401, detail="user authentication required")
    row = await get_or_create_profile_settings(db, user_id=user_id)

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return _serialize_profile(row)

    for key, value in patch.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    log.info(
        "profile-settings updated user_id=%s keys=%s",
        user_id,
        sorted(patch.keys()),
    )
    return _serialize_profile(row)


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


@router.get("/organization", response_model=OrganizationSettingsRead)
async def get_organization_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Return the org settings for the caller's current workspace."""
    row = await get_or_create_org_settings(db, workspace_id=workspace_id)
    return _serialize_org(row)


@router.put("/organization", response_model=OrganizationSettingsRead)
async def update_organization_settings(
    payload: OrganizationSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    # Side-effect dependency: 403s the caller when role < admin.
    _role: Annotated[str, Depends(require_workspace_role("admin"))],
):
    """Admin-gated PATCH update of org settings.

    Cross-workspace FK violations on ``default_brand_kit_id`` are caught
    *before* we write so a bad payload doesn't poison the row.
    """
    row = await get_or_create_org_settings(db, workspace_id=workspace_id)
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return _serialize_org(row)

    if (kit_id := patch.get("default_brand_kit_id")) is not None:
        await _verify_brand_kit_belongs(
            db, workspace_id=workspace_id, brand_kit_id=kit_id
        )

    for key, value in patch.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    log.info(
        "organization-settings updated workspace_id=%s keys=%s",
        workspace_id,
        sorted(patch.keys()),
    )
    return _serialize_org(row)


# ---------------------------------------------------------------------------
# Aggregate / effective
# ---------------------------------------------------------------------------


@router.get("", response_model=SettingsBundle)
async def get_settings_bundle(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
    scope: Annotated[
        str | None,
        Query(
            description=(
                "Optional filter — 'profile' or 'organization'. Omit for the full bundle."
            ),
            pattern="^(profile|organization|effective)$",
        ),
    ] = None,
):
    """One-shot fetch of profile + org + effective render defaults.

    The ``scope`` query parameter narrows the bundle so the React settings
    page can lazy-load tabs.
    """
    profile = None
    organization = None
    effective = None

    if scope in (None, "profile") and user_id is not None:
        row = await get_or_create_profile_settings(db, user_id=user_id)
        profile = UserProfileSettingsRead.model_validate(_serialize_profile(row))

    if scope in (None, "organization"):
        org_row = await get_or_create_org_settings(db, workspace_id=workspace_id)
        organization = OrganizationSettingsRead.model_validate(
            _serialize_org(org_row)
        )

    if scope in (None, "effective"):
        effective = await resolve_render_defaults(
            db, workspace_id=workspace_id, user_id=user_id
        )

    return SettingsBundle(
        profile=profile,
        organization=organization,
        effective=effective,
    )


@router.get("/effective", response_model=EffectiveRenderDefaults)
async def get_effective_render_defaults(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Return the resolved render defaults for the caller's request.

    Used by the mix-video and template-framework endpoints to fold org
    defaults onto a request payload.
    """
    return await resolve_render_defaults(
        db, workspace_id=workspace_id, user_id=user_id
    )


# ---------------------------------------------------------------------------
# App settings (global K/V)
# ---------------------------------------------------------------------------


@router.get("/app")
async def list_app_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    role: Annotated[str, Depends(require_workspace_role("guest"))],
    public_only: bool = Query(
        True,
        description=(
            "When True (default for non-admins), only ``is_public=True`` "
            "rows are returned."
        ),
    ),
):
    """List app settings.

    Non-admin callers always get ``public_only=True`` regardless of the
    query parameter — we filter to public rows automatically.
    """
    from app.core.permissions import role_at_least

    actually_public_only = public_only or not role_at_least(role, "admin")
    stmt = select(AppSetting).order_by(AppSetting.key.asc())
    if actually_public_only:
        stmt = stmt.where(AppSetting.is_public.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_app_setting(r) for r in rows]}


@router.get("/app/{key}", response_model=AppSettingRead)
async def get_app_setting(
    key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    role: Annotated[str, Depends(require_workspace_role("guest"))],
):
    stmt = select(AppSetting).where(AppSetting.key == key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"app setting {key!r} not found")
    if not row.is_public:
        from app.core.permissions import role_at_least

        if not role_at_least(role, "admin"):
            raise HTTPException(
                status_code=403,
                detail="this app setting is private to admins",
            )
    return _serialize_app_setting(row)


@router.post("/app", response_model=AppSettingRead, status_code=201)
async def create_app_setting(
    payload: AppSettingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_workspace_role("admin"))],
):
    stmt = select(AppSetting).where(AppSetting.key == payload.key)
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409, detail=f"app setting {payload.key!r} already exists"
        )
    row = AppSetting(
        key=payload.key,
        value=payload.value,
        description=payload.description,
        is_public=payload.is_public,
        updated_by=user_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    log.info(
        "app-setting created key=%s is_public=%s by=%s",
        row.key,
        row.is_public,
        user_id,
    )
    return _serialize_app_setting(row)


@router.put("/app/{key}", response_model=AppSettingRead)
async def update_app_setting(
    key: str,
    payload: AppSettingUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_workspace_role("admin"))],
):
    stmt = select(AppSetting).where(AppSetting.key == key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"app setting {key!r} not found")

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return _serialize_app_setting(row)
    for k, v in patch.items():
        setattr(row, k, v)
    row.updated_by = user_id
    await db.commit()
    await db.refresh(row)
    return _serialize_app_setting(row)


@router.delete("/app/{key}", status_code=200)
async def delete_app_setting(
    key: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[str, Depends(require_workspace_role("admin"))],
):
    stmt = select(AppSetting).where(AppSetting.key == key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"app setting {key!r} not found")
    await db.execute(delete(AppSetting).where(AppSetting.key == key))
    await db.commit()
    return {"ok": True, "key": key}


__all__ = ["router"]
