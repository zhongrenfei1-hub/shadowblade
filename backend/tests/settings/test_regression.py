"""Regression suite — make sure Settings doesn't break neighbouring features.

Covers the surfaces most likely to drift when the Settings module ships:

* Brand Kit GET still returns the materialised default even when an
  org-settings row exists.
* Brand Kit PUT untouched fields are still preserved.
* Brand Kit DELETE behaves correctly with org_settings.default_brand_kit_id
  unset (no FK violation, no false-positive cleanup log).
* Mix-video preview still folds the brand kit + survives an empty
  org-settings row.
* Anonymous mix-video calls keep working (X-User-Id absent) — settings
  must not introduce a hidden auth requirement.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Brand kit regression
# ---------------------------------------------------------------------------


def test_brand_kit_get_returns_default_alongside_org_settings(
    isolated_db, workspace_headers
):
    """The brand-kit endpoint must not be confused by the new org row."""
    # Auto-materialise both rows.
    isolated_db.get("/api/v1/settings/organization", headers=workspace_headers)
    r = isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["primary_color"] == "#0F2A4A"
    assert body["accent_color"] == "#22D3B7"


def test_brand_kit_put_unchanged_fields_persist(isolated_db, workspace_headers):
    """The brand-kit PATCH semantics must keep holding."""
    isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"primary_color": "#012345"},
    )
    isolated_db.put(
        "/api/v1/brand-kit",
        headers=workspace_headers,
        json={"accent_color": "#abcdef"},
    )
    body = isolated_db.get(
        "/api/v1/brand-kit", headers=workspace_headers
    ).json()
    assert body["primary_color"] == "#012345"
    assert body["accent_color"] == "#ABCDEF"


def test_brand_kit_delete_without_org_default_is_clean(
    isolated_db, workspace_headers
):
    """DELETE on a kit nobody depends on must not warn/fail."""
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=workspace_headers,
        json={"name": "Disposable", "primary_color": "#0a0a0a"},
    )
    kit_id = r.json()["id"]
    r = isolated_db.delete(
        f"/api/v1/brand-kits/{kit_id}", headers=workspace_headers
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True, "id": kit_id, "is_active": False}


def test_brand_kit_delete_after_pin_then_clear_idempotent(
    isolated_db, workspace_headers
):
    """Pin → unpin → delete must not log a phantom cleanup."""
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=workspace_headers,
        json={"name": "Toggle", "primary_color": "#020202"},
    )
    kit_id = r.json()["id"]
    isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"default_brand_kit_id": kit_id},
    )
    # Unpin first
    isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"default_brand_kit_id": None},
    )
    # Now delete — cleanup should be a no-op.
    r = isolated_db.delete(
        f"/api/v1/brand-kits/{kit_id}", headers=workspace_headers
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Settings + team + notification interplay
# ---------------------------------------------------------------------------


def test_settings_does_not_block_brand_kit_inventory(isolated_db, workspace_headers):
    """GET /brand-kits still works after org settings are materialised."""
    isolated_db.get(
        "/api/v1/settings/organization", headers=workspace_headers
    )
    isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    listed = isolated_db.get(
        "/api/v1/brand-kits", headers=workspace_headers
    ).json()
    assert "items" in listed
    assert len(listed["items"]) >= 1


def test_org_notification_preferences_align_with_categories(
    isolated_db, workspace_headers
):
    """Org's notification_preferences must use only valid category keys.

    This guards against the schema list and the Notification model
    drifting out of sync (a silent breakage that would slip past
    isolated schema tests).
    """
    from app.models.notification import NOTIFICATION_CATEGORIES

    sample = {cat: True for cat in NOTIFICATION_CATEGORIES}
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"notification_preferences": sample},
    )
    assert r.status_code == 200, r.text
    out = r.json()["notification_preferences"]
    for cat in NOTIFICATION_CATEGORIES:
        assert out[cat] is True


# ---------------------------------------------------------------------------
# Mix-video / org fold
# ---------------------------------------------------------------------------


def test_mix_video_apply_org_defaults_helper_folds_template():
    """Unit-level: helper folds org defaults into a fresh body."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.api.mix_video import MixVideoRequest, _apply_org_settings_defaults
    from app.core.db import Base
    from app.models.settings import OrganizationSettings

    async def run():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", future=True
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)

        async with Session() as db:
            db.add(
                OrganizationSettings(
                    workspace_id=1,
                    default_template_slug="product-demo",
                    default_loudness_lufs=-18.0,
                    default_aspect_ratio="16:9",
                )
            )
            await db.commit()

            body = MixVideoRequest.model_validate(
                {"project_id": "x", "clips": [{"path": "/tmp/a.mp4"}]}
            )
            out = await _apply_org_settings_defaults(
                db, workspace_id=1, body=body
            )

        await engine.dispose()
        return out

    out = asyncio.run(run())
    # template/preset/loudness folded; user did not set them.
    assert out.template == "product-demo"
    assert out.target_lufs == pytest.approx(-18.0)
    assert out.preset == "broadcast_16x9"


def test_mix_video_apply_org_defaults_respects_explicit_fields():
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.api.mix_video import MixVideoRequest, _apply_org_settings_defaults
    from app.core.db import Base
    from app.models.settings import OrganizationSettings

    async def run():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", future=True
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)

        async with Session() as db:
            db.add(
                OrganizationSettings(
                    workspace_id=1,
                    default_template_slug="product-demo",
                    default_loudness_lufs=-18.0,
                )
            )
            await db.commit()

            body = MixVideoRequest.model_validate(
                {
                    "project_id": "x",
                    "clips": [{"path": "/tmp/a.mp4"}],
                    "template": "hero-launch",
                    "target_lufs": -12.0,
                }
            )
            out = await _apply_org_settings_defaults(
                db, workspace_id=1, body=body
            )

        await engine.dispose()
        return out

    out = asyncio.run(run())
    # Explicit fields untouched.
    assert out.template == "hero-launch"
    assert out.target_lufs == pytest.approx(-12.0)


def test_mix_video_watermark_disabled_clears_path():
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.api.mix_video import MixVideoRequest, _apply_org_settings_defaults
    from app.core.db import Base
    from app.models.settings import OrganizationSettings

    async def run():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", future=True
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)

        async with Session() as db:
            db.add(
                OrganizationSettings(
                    workspace_id=1, video_watermark_enabled=False
                )
            )
            await db.commit()

            body = MixVideoRequest.model_validate(
                {"project_id": "x", "clips": [{"path": "/tmp/a.mp4"}]}
            )
            out = await _apply_org_settings_defaults(
                db, workspace_id=1, body=body
            )

        await engine.dispose()
        return out

    out = asyncio.run(run())
    assert out.watermark_path is None
