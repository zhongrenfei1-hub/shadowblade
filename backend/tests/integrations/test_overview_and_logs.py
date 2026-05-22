"""Overview + audit log tests (5 cases).

The overview is the dashboard widget; the logs endpoint is the recent-
events drawer. Both must filter by workspace and return tidy counts.
"""

from __future__ import annotations


def test_overview_empty_workspace(isolated_db, workspace_headers):
    r = isolated_db.get("/api/v1/integrations/overview", headers=workspace_headers)
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "api_keys_active": 0,
        "api_keys_total": 0,
        "webhooks_active": 0,
        "webhooks_total": 0,
        "third_party_active": 0,
        "third_party_total": 0,
        "recent_events": [],
    }


def test_overview_counts_active_vs_total(
    isolated_db, workspace_headers, api_key_factory, mock_http_server
):
    # Two keys, one revoked
    _, k1 = api_key_factory(name="a")
    api_key_factory(name="b")
    isolated_db.delete(
        f"/api/v1/integrations/api-keys/{k1['id']}", headers=workspace_headers
    )

    # One webhook (active)
    isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "h", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    # One third-party (active)
    isolated_db.post(
        "/api/v1/integrations/third-party",
        json={
            "name": "tp",
            "provider": "slack",
            "config": {"webhook_url": mock_http_server["url"]},
        },
        headers=workspace_headers,
    )

    r = isolated_db.get("/api/v1/integrations/overview", headers=workspace_headers)
    body = r.json()
    assert body["api_keys_total"] == 2
    assert body["api_keys_active"] == 1
    assert body["webhooks_total"] == 1
    assert body["webhooks_active"] == 1
    assert body["third_party_total"] == 1


def test_logs_endpoint_filter_by_webhook(
    isolated_db, workspace_headers, mock_http_server
):
    create = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "h", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    wh_id = create.json()["id"]
    # Drive two test deliveries
    isolated_db.post(
        f"/api/v1/integrations/webhooks/{wh_id}/test", headers=workspace_headers
    )
    isolated_db.post(
        f"/api/v1/integrations/webhooks/{wh_id}/test", headers=workspace_headers
    )

    r = isolated_db.get(
        f"/api/v1/integrations/logs?webhook_id={wh_id}", headers=workspace_headers
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    for item in items:
        assert item["webhook_id"] == wh_id
        assert item["status"] == "success"


def test_logs_endpoint_filter_by_event_type(
    isolated_db, workspace_headers, mock_http_server
):
    # Subscribe a webhook to BOTH events
    isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "fanout",
            "target_url": mock_http_server["url"],
            "event_types": [],
        },
        headers=workspace_headers,
    )
    isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=video_generated",
        json={},
        headers=workspace_headers,
    )
    isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=brand_kit_updated",
        json={},
        headers=workspace_headers,
    )

    # Filter
    r = isolated_db.get(
        "/api/v1/integrations/logs?event_type=brand_kit_updated",
        headers=workspace_headers,
    )
    items = r.json()["items"]
    assert all(it["event_type"] == "brand_kit_updated" for it in items)
    assert len(items) >= 1


def test_logs_endpoint_workspace_isolation(
    isolated_db, workspace_headers, mock_http_server
):
    """Workspace A's logs never bleed into workspace B."""
    isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "h", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    isolated_db.post(
        "/api/v1/integrations/events/emit?event_type=video_generated",
        json={},
        headers=workspace_headers,
    )

    r_other = isolated_db.get(
        "/api/v1/integrations/logs", headers={"X-Workspace-Id": "2"}
    )
    assert r_other.status_code == 200
    assert r_other.json()["items"] == []
