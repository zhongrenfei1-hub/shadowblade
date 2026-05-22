"""End-to-end event dispatch tests (5 cases).

Each test wires up real subscribers and confirms that calls into the
event hook fire actual outbound POSTs against the mock server.
"""

from __future__ import annotations

import asyncio

from app.services.integrations.webhook_service import verify_signature


def test_emit_event_fires_subscribed_webhook(isolated_db, workspace_headers, mock_http_server):
    # Subscribe to video_generated only
    create = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "vg",
            "target_url": mock_http_server["url"],
            "event_types": ["video_generated"],
        },
        headers=workspace_headers,
    )
    secret = create.json()["secret"]

    r = isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=video_generated",
        json={"task_id": "tst", "project_id": 1, "workspace_id": 1},
        headers=workspace_headers,
    )
    assert r.status_code == 200, r.text

    assert len(mock_http_server["received"]) == 1
    sent = mock_http_server["received"][0]
    assert sent["headers"]["X-Shadowblade-Event"] == "video_generated"
    assert verify_signature(
        secret,
        sent["body"].encode("utf-8"),
        sent["headers"]["X-Shadowblade-Signature"],
    )


def test_emit_event_skips_non_subscribed(isolated_db, workspace_headers, mock_http_server):
    isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "only-failed",
            "target_url": mock_http_server["url"],
            "event_types": ["video_failed"],
        },
        headers=workspace_headers,
    )

    r = isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=video_generated",
        json={"task_id": "tst"},
        headers=workspace_headers,
    )
    assert r.status_code == 200
    assert mock_http_server["received"] == []  # No delivery


def test_empty_event_types_means_subscribe_all(isolated_db, workspace_headers, mock_http_server):
    isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "fanout",
            "target_url": mock_http_server["url"],
            "event_types": [],  # empty = all
        },
        headers=workspace_headers,
    )

    isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=brand_kit_updated",
        json={"brand_kit_id": 1},
        headers=workspace_headers,
    )
    isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=template_updated",
        json={"name": "vlog_warm"},
        headers=workspace_headers,
    )
    assert len(mock_http_server["received"]) == 2


def test_inactive_webhooks_do_not_receive_events(isolated_db, workspace_headers, mock_http_server):
    create = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "off", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    wh_id = create.json()["id"]
    # Disable
    isolated_db.put(
        f"/api/v1/integrations/webhooks/{wh_id}",
        json={"is_active": False},
        headers=workspace_headers,
    )

    isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=video_generated",
        json={"task_id": "tst"},
        headers=workspace_headers,
    )
    assert mock_http_server["received"] == []


def test_brand_kit_update_emits_event(isolated_db, workspace_headers, mock_http_server):
    """PUT /brand-kit fires brand_kit_updated through to webhooks."""
    isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "brand-listener",
            "target_url": mock_http_server["url"],
            "event_types": ["brand_kit_updated"],
        },
        headers=workspace_headers,
    )
    # Drive a brand-kit PUT
    r = isolated_db.put(
        "/api/v1/brand-kit",
        json={"name": "Renamed Kit"},
        headers=workspace_headers,
    )
    assert r.status_code == 200, r.text

    # Tiny grace period — the emission is awaited inline but the
    # HTTP layer to the mock server runs on a different thread.
    import time

    for _ in range(50):
        if mock_http_server["received"]:
            break
        time.sleep(0.02)
    assert len(mock_http_server["received"]) >= 1
    sent = mock_http_server["received"][0]
    assert sent["headers"]["X-Shadowblade-Event"] == "brand_kit_updated"
