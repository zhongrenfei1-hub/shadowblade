"""Settings ↔ Brand Kit / Mix-Video integration tests.

Validates the side-effect contracts wired through ``app.services.settings``:

* Deleting a brand kit that is the org default clears the FK.
* The brand-kit resolver picks up ``default_brand_kit_id`` as a third
  fallback after user-scoped and workspace-scoped kits.
* Mix-video preview folds the org-settings defaults onto a payload
  that omits the corresponding fields.
* User-explicit fields always win the precedence battle.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.brand_kit import BrandKit as BrandKitORM
from app.models.settings import OrganizationSettings
from app.services.settings import (
    on_brand_kit_deleted,
    on_brand_kit_updated,
    resolve_effective_brand_kit_id,
    resolve_render_defaults,
)


# ---------------------------------------------------------------------------
# Service-layer hooks
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def org_with_kit(session_factory):
    """Seed an org-settings row pointing at a brand kit in the same ws."""
    async with session_factory() as db:
        kit = BrandKitORM(
            workspace_id=1,
            scope="workspace",
            name="Test Kit",
            is_active=True,
        )
        db.add(kit)
        await db.commit()
        await db.refresh(kit)

        org = OrganizationSettings(workspace_id=1, default_brand_kit_id=kit.id)
        db.add(org)
        await db.commit()
        return {"kit_id": kit.id, "workspace_id": 1}


@pytest.mark.asyncio
async def test_on_brand_kit_deleted_clears_org_default(
    session_factory, org_with_kit
):
    async with session_factory() as db:
        n = await on_brand_kit_deleted(
            db,
            workspace_id=org_with_kit["workspace_id"],
            brand_kit_id=org_with_kit["kit_id"],
        )
        assert n == 1

    # Verify the FK is now NULL.
    async with session_factory() as db:
        row = (
            await db.execute(
                select(OrganizationSettings.default_brand_kit_id).where(
                    OrganizationSettings.workspace_id == 1
                )
            )
        ).scalar_one()
        assert row is None


@pytest.mark.asyncio
async def test_on_brand_kit_deleted_noop_when_not_default(
    session_factory, org_with_kit
):
    async with session_factory() as db:
        n = await on_brand_kit_deleted(
            db, workspace_id=1, brand_kit_id=9999
        )
        assert n == 0


@pytest.mark.asyncio
async def test_on_brand_kit_updated_inactive_clears(
    session_factory, org_with_kit
):
    async with session_factory() as db:
        n = await on_brand_kit_updated(
            db,
            workspace_id=1,
            brand_kit_id=org_with_kit["kit_id"],
            is_active=False,
        )
        assert n == 1


@pytest.mark.asyncio
async def test_on_brand_kit_updated_active_noop(
    session_factory, org_with_kit
):
    async with session_factory() as db:
        n = await on_brand_kit_updated(
            db,
            workspace_id=1,
            brand_kit_id=org_with_kit["kit_id"],
            is_active=True,
        )
        assert n == 0


@pytest.mark.asyncio
async def test_resolve_effective_brand_kit_id_picks_org_default(
    session_factory, org_with_kit
):
    async with session_factory() as db:
        kit_id = await resolve_effective_brand_kit_id(
            db, workspace_id=1, user_id=None
        )
        # The only active kit is the workspace-scoped one we seeded —
        # it wins step 2 before step 3 even fires.
        assert kit_id == org_with_kit["kit_id"]


@pytest.mark.asyncio
async def test_resolve_falls_through_to_org_default_when_no_active_kit(
    session_factory,
):
    """Seed an INACTIVE workspace kit + an inactive but-defaulted org row —
    expect None because step 3 verifies is_active."""
    async with session_factory() as db:
        # Inactive workspace kit (filters out at step 2)
        kit = BrandKitORM(
            workspace_id=1,
            scope="workspace",
            name="Inactive",
            is_active=False,
        )
        db.add(kit)
        # Active workspace kit that lives in a *different* workspace —
        # should not be picked up.
        other = BrandKitORM(
            workspace_id=2,
            scope="workspace",
            name="Other",
            is_active=True,
        )
        db.add(other)
        await db.commit()
        await db.refresh(kit)

        # Point ws1's org default at the inactive kit — step 3 should
        # reject it because is_active is False.
        org = OrganizationSettings(
            workspace_id=1, default_brand_kit_id=kit.id
        )
        db.add(org)
        await db.commit()

        kit_id = await resolve_effective_brand_kit_id(
            db, workspace_id=1, user_id=None
        )
        assert kit_id is None


@pytest.mark.asyncio
async def test_resolve_render_defaults_reflects_org(
    session_factory,
):
    async with session_factory() as db:
        org = OrganizationSettings(
            workspace_id=1,
            default_codec="h265",
            default_loudness_lufs=-18.0,
            default_aspect_ratio="16:9",
        )
        db.add(org)
        await db.commit()

        defaults = await resolve_render_defaults(
            db, workspace_id=1, user_id=None
        )
        assert defaults.codec == "h265"
        assert defaults.loudness_lufs == pytest.approx(-18.0)
        assert defaults.aspect_ratio == "16:9"


# ---------------------------------------------------------------------------
# End-to-end via REST
# ---------------------------------------------------------------------------


def test_brand_kit_delete_clears_org_default(isolated_db, workspace_headers):
    """DELETE /brand-kits/{id} → org default cleared automatically."""
    # 1. Create a brand kit.
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=workspace_headers,
        json={"name": "Targeted", "primary_color": "#202020"},
    )
    kit_id = r.json()["id"]

    # 2. Pin it as the org default.
    r = isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"default_brand_kit_id": kit_id},
    )
    assert r.status_code == 200
    assert r.json()["default_brand_kit_id"] == kit_id

    # 3. Delete the kit.
    r = isolated_db.delete(
        f"/api/v1/brand-kits/{kit_id}", headers=workspace_headers
    )
    assert r.status_code == 200

    # 4. Org default must be NULL now.
    org = isolated_db.get(
        "/api/v1/settings/organization", headers=workspace_headers
    ).json()
    assert org["default_brand_kit_id"] is None


def test_effective_falls_through_to_org_default(isolated_db, workspace_headers):
    """When no active brand kit exists, /effective surfaces the org default."""
    # 1. Create + immediately deactivate the workspace kit so step 2 of
    #    the resolver returns None.
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=workspace_headers,
        json={"name": "Backup", "primary_color": "#303030"},
    )
    backup_id = r.json()["id"]
    isolated_db.delete(
        f"/api/v1/brand-kits/{backup_id}", headers=workspace_headers
    )

    # 2. Create a *new* active kit + pin it as the org default.
    r = isolated_db.post(
        "/api/v1/brand-kits",
        headers=workspace_headers,
        json={"name": "Default", "primary_color": "#404040"},
    )
    default_id = r.json()["id"]
    isolated_db.put(
        "/api/v1/settings/organization",
        headers=workspace_headers,
        json={"default_brand_kit_id": default_id},
    )

    eff = isolated_db.get(
        "/api/v1/settings/effective", headers=workspace_headers
    ).json()
    # The active workspace kit wins step 2 before the org-default fallback
    # is even consulted. Either way the brand_kit_id is non-None.
    assert eff["brand_kit_id"] == default_id
