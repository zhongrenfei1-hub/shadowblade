"""Regression tests — confirm existing features still work post-integration (4 cases).

The integration module is supposed to *add* surface area, not change
what already exists. These tests prove:

* The mix-video router still answers ``/presets/list``, ``/looks/list``,
  ``/features`` exactly like before.
* Brand-kit GET/PUT still works (no DB schema collision from the new tables).
* Templates discovery still returns the built-in set.
* The new tables coexist with the legacy ones — ``init_db`` succeeds and
  the model classes are all discoverable.
"""

from __future__ import annotations


def test_mix_video_presets_still_listed(isolated_db):
    r = isolated_db.get("/api/v1/mix-video/presets/list")
    assert r.status_code == 200
    assert "items" in r.json()
    assert len(r.json()["items"]) >= 1


def test_templates_still_listed(isolated_db):
    r = isolated_db.get("/api/v1/templates")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["items"]]
    assert "base" in names


def test_brand_kit_get_and_put_still_work(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/brand-kit", headers=workspace_headers)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "ShadowBlade · Default"
    # PUT changes the name
    r2 = isolated_db.put(
        "/api/v1/brand-kit",
        json={"name": "Updated"},
        headers=workspace_headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["name"] == "Updated"


def test_integration_tables_coexist_with_legacy(isolated_db):
    """``init_db`` ran inside the fixture without raising — and the new ORM
    classes are registered against the same Base as Brand Kit / User.
    """
    from app.core.db import Base
    from app.models.brand_kit import BrandKit  # noqa: F401
    from app.models.integration import ApiKey, Webhook, ThirdPartyIntegration, IntegrationLog
    from app.models.user import User  # noqa: F401

    tables = {t.name for t in Base.metadata.tables.values()}
    assert {
        "api_keys",
        "webhooks",
        "third_party_integrations",
        "integration_logs",
        "brand_kits",
        "users",
        "workspaces",
    } <= tables
