"""REST endpoints for Brand Kit configuration.

Two route families share a single :class:`APIRouter`:

* Singular (the *current* kit for the caller's workspace/user)
    - ``GET    /api/v1/brand-kit``      — resolved active kit (user > ws > default)
    - ``PUT    /api/v1/brand-kit``      — PATCH-style update (auto-create on first call)
    - ``POST   /api/v1/brand-kit/logo`` — upload a logo, attach to active kit

* Plural / legacy (workspace inventory & fixtures-flavoured demo data)
    - ``GET    /api/v1/brand-kits``     — list every kit in this workspace
    - ``POST   /api/v1/brand-kits``     — create another kit (e.g. event-specific)
    - ``DELETE /api/v1/brand-kits/{id}``— deactivate a non-default kit

The resolution policy is documented on :func:`_resolve_active_kit` —
user-scoped wins over workspace-scoped wins over a freshly-defaulted kit
materialised on first read.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user_id,
    get_current_workspace_id,
    get_db,
)
from app.models.brand_kit import BrandKit as BrandKitORM
from app.schemas.brand_kit import (
    BrandKitCreate,
    BrandKitLogoResponse,
    BrandKitRead,
    BrandKitUpdate,
)
from app.services import notifications as notifications_svc
from app.services.fixtures import brand_kit_fixture
from app.services.settings import on_brand_kit_deleted, on_brand_kit_updated
from app.services.storage import (
    ALLOWED_LOGO_EXTENSIONS,
    MAX_LOGO_BYTES,
    public_url_for,
    save_brand_logo,
)

log = logging.getLogger("shadowblade.api.brand_kits")
router = APIRouter(tags=["brand_kits"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _serialize(row: BrandKitORM) -> dict[str, Any]:
    """ORM → JSON-safe dict.

    Pydantic's ``from_attributes`` would handle this if we never had to
    look at the dict between read and response, but having an explicit
    serializer means tests and the file-upload endpoint can both round-trip
    without paying for full validation.
    """
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "scope": row.scope,
        "owner_id": row.owner_id,
        "is_active": row.is_active,
        "name": row.name,
        "primary_color": row.primary_color,
        "secondary_color": row.secondary_color,
        "accent_color": row.accent_color,
        "neutral_color": row.neutral_color,
        "background_color": row.background_color,
        "font_family": row.font_family,
        "font_heading": row.font_heading,
        "font_body": row.font_body,
        "logo_url": row.logo_url,
        "logo_mono_url": row.logo_mono_url,
        "intro_url": row.intro_url,
        "outro_url": row.outro_url,
        "watermark_text": row.watermark_text,
        "watermark_opacity": row.watermark_opacity,
        "watermark_position": row.watermark_position,
        "watermark_width_pct": row.watermark_width_pct,
        "voice": row.voice,
        "target_lufs": row.target_lufs,
        "target_tp": row.target_tp,
        "bgm_gain_db": row.bgm_gain_db,
        "subtitle_size": row.subtitle_size,
        "subtitle_margin_v": row.subtitle_margin_v,
        "default_template_name": row.default_template_name,
        "custom_css_snippet": row.custom_css_snippet,
        "tone": row.tone or {},
        "created_at": _isoformat(row.created_at),
        "updated_at": _isoformat(row.updated_at),
    }


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


async def _resolve_active_kit(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int | None,
) -> BrandKitORM | None:
    """Resolution order: user-scoped active → workspace-scoped active → None.

    Both lookups filter on ``is_active=True`` so deactivated/historic kits
    are skipped. Order is by descending ``id`` to deterministically pick
    the most recently created one if (by mistake) two are flagged active.
    """
    if user_id is not None:
        stmt = (
            select(BrandKitORM)
            .where(
                BrandKitORM.workspace_id == workspace_id,
                BrandKitORM.scope == "user",
                BrandKitORM.owner_id == user_id,
                BrandKitORM.is_active.is_(True),
            )
            .order_by(BrandKitORM.id.desc())
            .limit(1)
        )
        result = (await db.execute(stmt)).scalars().first()
        if result is not None:
            return result

    stmt = (
        select(BrandKitORM)
        .where(
            BrandKitORM.workspace_id == workspace_id,
            BrandKitORM.scope == "workspace",
            BrandKitORM.is_active.is_(True),
        )
        .order_by(BrandKitORM.id.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalars().first()


async def _materialize_default_kit(
    db: AsyncSession,
    *,
    workspace_id: int,
) -> BrandKitORM:
    """First-PUT helper — create a workspace-scoped kit with all defaults.

    Lets the API behave as if a kit *always* exists, even before the user
    has ever opened the Brand Kit page. The defaults match the BrandKit
    dataclass in :mod:`app.services.video.brand`.
    """
    row = BrandKitORM(
        workspace_id=workspace_id,
        scope="workspace",
        owner_id=None,
        is_active=True,
        name="ShadowBlade · Default",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Singular routes — current active kit
# ---------------------------------------------------------------------------


@router.get("/brand-kit", response_model=BrandKitRead)
async def get_active_brand_kit(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Return the active brand kit for the caller.

    If neither a user-scoped nor a workspace-scoped active kit exists, we
    materialise a workspace-default one on the fly so the frontend never
    has to special-case the empty state.
    """
    kit = await _resolve_active_kit(db, workspace_id=workspace_id, user_id=user_id)
    if kit is None:
        kit = await _materialize_default_kit(db, workspace_id=workspace_id)
    return _serialize(kit)


@router.put("/brand-kit", response_model=BrandKitRead)
async def update_active_brand_kit(
    payload: BrandKitUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Patch the caller's active kit; create one with defaults if missing.

    Only keys present in the request body are written — other fields keep
    their stored value. Hex-colour validation happens in the Pydantic
    layer, so anything we see here is already canonical.
    """
    kit = await _resolve_active_kit(db, workspace_id=workspace_id, user_id=user_id)
    if kit is None:
        kit = await _materialize_default_kit(db, workspace_id=workspace_id)

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return _serialize(kit)

    for key, value in patch.items():
        setattr(kit, key, value)
    await db.commit()
    await db.refresh(kit)
    log.info(
        "brand-kit updated id=%s workspace=%s scope=%s keys=%s",
        kit.id,
        kit.workspace_id,
        kit.scope,
        list(patch),
    )
    # Inbox event — fire-and-forget. ``notify_brand_kit_changed`` swallows
    # its own exceptions so this never breaks the PUT.
    await notifications_svc.notify_brand_kit_changed(
        workspace_id=workspace_id,
        user_id=user_id,
        kit_id=kit.id,
        kit_name=kit.name,
        changed_keys=list(patch),
        actor_id=user_id,
        db=db,
    )
    # Fan the change out to subscribed webhooks / third-party integrations.
    try:
        from app.services.integrations.events import emit_event

        await emit_event(
            workspace_id=workspace_id,
            event_type="brand_kit_updated",
            payload={
                "brand_kit_id": kit.id,
                "workspace_id": workspace_id,
                "scope": kit.scope,
                "fields_changed": list(patch),
            },
        )
    except Exception:  # noqa: BLE001
        log.exception("emit_event(brand_kit_updated) failed for id=%s", kit.id)
    return _serialize(kit)


@router.post("/brand-kit/logo", response_model=BrandKitLogoResponse)
async def upload_brand_kit_logo(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
    field: Annotated[str, Form()] = "logo_url",
):
    """Upload an image; persist its public URL on the active kit.

    ``field`` lets the caller decide which slot to update (``logo_url``,
    ``logo_mono_url``, ``intro_url``, ``outro_url``). Anything else
    400s. The file is validated for extension + content-type + byte cap,
    then optionally decoded with Pillow so we can return dimensions.
    """
    allowed_fields = {"logo_url", "logo_mono_url", "intro_url", "outro_url"}
    if field not in allowed_fields:
        raise HTTPException(
            status_code=400,
            detail=f"field must be one of {sorted(allowed_fields)}",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="upload missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"unsupported extension {ext!r}; allowed: "
                + ", ".join(sorted(ALLOWED_LOGO_EXTENSIONS))
            ),
        )
    expected_ct = ALLOWED_LOGO_EXTENSIONS[ext]
    if file.content_type and file.content_type != expected_ct:
        # We're forgiving on content-type — some clients send octet-stream.
        log.debug(
            "logo upload content-type %s for %s (expected %s)",
            file.content_type,
            ext,
            expected_ct,
        )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="empty upload body")
    if len(data) > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"logo too large: {len(data)} bytes (max {MAX_LOGO_BYTES})",
        )

    width: int | None = None
    height: int | None = None
    if ext != ".svg":
        # Bitmap formats decode through Pillow; SVG is left as-is.
        try:
            from PIL import Image  # local import keeps import cost off cold paths

            with Image.open(io.BytesIO(data)) as img:
                width, height = img.size
                img.verify()  # raises if the file is corrupt
        except Exception as exc:  # noqa: BLE001 — surfaced to the client
            raise HTTPException(
                status_code=400, detail=f"image decode failed: {exc}"
            ) from exc

    saved = save_brand_logo(
        workspace_id=workspace_id, filename=file.filename, data=data
    )
    url = public_url_for(saved)

    # Attach to the active kit (materialise if absent).
    kit = await _resolve_active_kit(db, workspace_id=workspace_id, user_id=user_id)
    if kit is None:
        kit = await _materialize_default_kit(db, workspace_id=workspace_id)
    setattr(kit, field, url)
    await db.commit()
    await db.refresh(kit)

    # Inbox event for the asset upload — surfaces "Acme just refreshed
    # their logo" to teammates watching the brand kit.
    await notifications_svc.notify_brand_kit_changed(
        workspace_id=workspace_id,
        user_id=user_id,
        kit_id=kit.id,
        kit_name=kit.name,
        changed_keys=[field],
        actor_id=user_id,
        db=db,
    )

    return BrandKitLogoResponse(
        url=url,
        bytes=len(data),
        content_type=expected_ct,
        width=width,
        height=height,
    )


# ---------------------------------------------------------------------------
# Plural routes — inventory & legacy compat
# ---------------------------------------------------------------------------


@router.get("/brand-kits")
async def list_brand_kits(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """List every brand kit in the caller's workspace.

    Falls back to the fixtures payload when the DB is empty so the demo
    frontend still has something to render (matches behaviour pre-rewrite).
    """
    stmt = (
        select(BrandKitORM)
        .where(BrandKitORM.workspace_id == workspace_id)
        .order_by(BrandKitORM.id.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        return brand_kit_fixture()
    return {"items": [_serialize(r) for r in rows]}


@router.post("/brand-kits", response_model=BrandKitRead, status_code=201)
async def create_brand_kit(
    payload: BrandKitCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Create another brand kit (e.g. an event-specific palette).

    Marking ``is_active=True`` will *not* auto-deactivate the existing
    active kit — callers can run multiple active kits side-by-side as long
    as their (scope, owner_id) tuples differ. Use ``DELETE`` to turn one
    off explicitly.
    """
    data = payload.model_dump()
    row = BrandKitORM(workspace_id=workspace_id, **data)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _serialize(row)


@router.delete("/brand-kits/{kit_id}", status_code=200)
async def deactivate_brand_kit(
    kit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Soft-delete by flipping ``is_active`` to ``False``.

    We never hard-delete: historical render jobs may still reference the
    palette via the templates folded at render-time, and keeping the row
    around makes those traces useful for audit.
    """
    stmt = select(BrandKitORM).where(
        BrandKitORM.id == kit_id, BrandKitORM.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="brand kit not found")
    row.is_active = False
    await db.commit()
    # Referential cleanup: if this kit was the org-wide default, clear that
    # pointer so the resolver doesn't pick a deactivated row. ``on_brand_kit_
    # deleted`` runs its own commit and is a no-op when the FK isn't set.
    await on_brand_kit_deleted(
        db, workspace_id=workspace_id, brand_kit_id=kit_id
    )
    return {"ok": True, "id": kit_id, "is_active": False}


__all__ = ["router"]
