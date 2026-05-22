"""Third-party integrations + provider adapter tests (8 cases)."""

from __future__ import annotations

import asyncio

import pytest

from app.services.integrations.providers import (
    PROVIDER_REGISTRY,
    UnsupportedProviderError,
    get_provider,
)


# --------------------------------------------------------------------------- #
# Discovery                                                                    #
# --------------------------------------------------------------------------- #


def test_provider_catalog_returns_known_slugs(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/integrations/providers", headers=workspace_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    slugs = {p["slug"] for p in items}
    assert {"slack", "discord", "notion", "zapier", "generic_webhook"} <= slugs
    # Every entry has the documented fields
    for p in items:
        assert {"slug", "label", "description", "config_hint", "supports_test"} <= set(p.keys())


def test_provider_registry_includes_all_documented(isolated_db, workspace_headers):
    """The Python registry and the catalog endpoint must stay in lockstep."""
    r = isolated_db.get("/api/v1/integrations/providers", headers=workspace_headers)
    catalog_slugs = {p["slug"] for p in r.json()["items"]}
    registry_slugs = set(PROVIDER_REGISTRY.keys())
    assert catalog_slugs == registry_slugs


def test_get_provider_unknown_raises():
    with pytest.raises(UnsupportedProviderError):
        get_provider("not_a_real_provider")


# --------------------------------------------------------------------------- #
# CRUD                                                                         #
# --------------------------------------------------------------------------- #


def test_create_third_party_integration(isolated_db, workspace_headers, mock_http_server):
    r = isolated_db.post(
        "/api/v1/integrations/third-party",
        json={
            "name": "Eng channel",
            "provider": "slack",
            "description": "Posts to #renders",
            "config": {"webhook_url": mock_http_server["url"]},
            "event_types": ["video_generated"],
        },
        headers=workspace_headers,
    )
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["provider"] == "slack"
    assert out["event_types"] == ["video_generated"]


def test_create_third_party_rejects_unknown_provider(isolated_db, workspace_headers):
    r = isolated_db.post(
        "/api/v1/integrations/third-party",
        json={"name": "nope", "provider": "blockchain", "config": {}},
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_third_party_config_redaction_in_response(isolated_db, workspace_headers):
    """Secret-looking config keys are masked in API responses."""
    r = isolated_db.post(
        "/api/v1/integrations/third-party",
        json={
            "name": "notion",
            "provider": "notion",
            "config": {"token": "secret_token_12345", "database_id": "db123"},
        },
        headers=workspace_headers,
    )
    assert r.status_code == 201
    out = r.json()
    assert out["config"]["token"].startswith("•••")
    assert "2345" in out["config"]["token"]
    # Non-sensitive fields stay verbatim
    assert out["config"]["database_id"] == "db123"


def test_update_third_party_integration(isolated_db, workspace_headers, mock_http_server):
    create = isolated_db.post(
        "/api/v1/integrations/third-party",
        json={
            "name": "first",
            "provider": "slack",
            "config": {"webhook_url": mock_http_server["url"]},
        },
        headers=workspace_headers,
    )
    integration_id = create.json()["id"]
    r = isolated_db.put(
        f"/api/v1/integrations/third-party/{integration_id}",
        json={"name": "renamed", "is_active": False},
        headers=workspace_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"
    assert r.json()["is_active"] is False


def test_delete_third_party_is_soft(isolated_db, workspace_headers, mock_http_server):
    create = isolated_db.post(
        "/api/v1/integrations/third-party",
        json={
            "name": "first",
            "provider": "slack",
            "config": {"webhook_url": mock_http_server["url"]},
        },
        headers=workspace_headers,
    )
    integration_id = create.json()["id"]
    r = isolated_db.delete(
        f"/api/v1/integrations/third-party/{integration_id}", headers=workspace_headers
    )
    assert r.status_code == 200
    listing = isolated_db.get(
        "/api/v1/integrations/third-party", headers=workspace_headers
    ).json()
    assert listing["items"][0]["is_active"] is False


# --------------------------------------------------------------------------- #
# Adapter delivery (Slack / Discord / Generic via mock server)                  #
# --------------------------------------------------------------------------- #


def test_slack_adapter_delivers(mock_http_server):
    adapter = PROVIDER_REGISTRY["slack"]

    async def _go():
        result = await adapter.deliver(
            event_type="video_generated",
            payload={"project_id": 42, "title": "test"},
            config={"webhook_url": mock_http_server["url"]},
        )
        assert result.ok is True
        assert mock_http_server["received"][0]["json"]["text"].startswith("[video_generated]")

    asyncio.get_event_loop().run_until_complete(_go())


def test_generic_webhook_passes_event_and_payload(mock_http_server):
    adapter = PROVIDER_REGISTRY["generic_webhook"]

    async def _go():
        await adapter.deliver(
            event_type="ping",
            payload={"hello": "world"},
            config={"url": mock_http_server["url"]},
        )
        sent = mock_http_server["received"][0]["json"]
        assert sent == {"event": "ping", "payload": {"hello": "world"}}

    asyncio.get_event_loop().run_until_complete(_go())


def test_slack_adapter_refuses_missing_webhook_url():
    adapter = PROVIDER_REGISTRY["slack"]

    async def _go():
        with pytest.raises(UnsupportedProviderError):
            await adapter.deliver(
                event_type="ping",
                payload={},
                config={},  # no webhook_url
            )

    asyncio.get_event_loop().run_until_complete(_go())
