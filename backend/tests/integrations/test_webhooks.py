"""Webhook CRUD + delivery + signature tests (12 cases).

These tests stand up a real recording HTTP server (see ``conftest.py``)
so the full path — sign → POST → record audit log → bump health
counters — is exercised end-to-end with no mocks.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.services.integrations.webhook_service import (
    deliver_webhook,
    sign_payload,
    verify_signature,
)


# --------------------------------------------------------------------------- #
# Pure helpers                                                                 #
# --------------------------------------------------------------------------- #


def test_sign_payload_is_deterministic():
    body = b'{"hello":"world"}'
    assert sign_payload("topsecret", body) == sign_payload("topsecret", body)


def test_sign_payload_differs_per_secret():
    body = b'{"hello":"world"}'
    assert sign_payload("a", body) != sign_payload("b", body)


def test_verify_signature_round_trip():
    body = b"payload"
    sig = sign_payload("shh", body)
    assert verify_signature("shh", body, sig)
    assert not verify_signature("shh", body, "sha256=deadbeef")
    assert not verify_signature("wrong", body, sig)


# --------------------------------------------------------------------------- #
# CRUD via TestClient                                                          #
# --------------------------------------------------------------------------- #


def test_create_webhook_returns_secret_once(isolated_db, workspace_headers, mock_http_server):
    r = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "mock",
            "target_url": mock_http_server["url"],
            "event_types": ["video_generated"],
        },
        headers=workspace_headers,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["secret"]
    assert len(body["secret"]) >= 16
    # GET list does NOT include the full secret
    listing = isolated_db.get("/api/v1/integrations/webhooks", headers=workspace_headers).json()
    item = listing["items"][0]
    assert "secret" not in item
    assert item["secret_preview"].startswith("•••")


def test_create_webhook_rejects_invalid_url(isolated_db, workspace_headers):
    r = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "bad", "target_url": "not-a-url"},
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_create_webhook_rejects_unknown_event_type(isolated_db, workspace_headers, mock_http_server):
    r = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "bad",
            "target_url": mock_http_server["url"],
            "event_types": ["this_event_does_not_exist"],
        },
        headers=workspace_headers,
    )
    assert r.status_code == 422


def test_update_webhook_patches(isolated_db, workspace_headers, mock_http_server):
    r = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "before", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    wh_id = r.json()["id"]
    r2 = isolated_db.put(
        f"/api/v1/integrations/webhooks/{wh_id}",
        json={"name": "after", "is_active": False},
        headers=workspace_headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["name"] == "after"
    assert r2.json()["is_active"] is False


def test_delete_webhook_is_soft(isolated_db, workspace_headers, mock_http_server):
    wh_id = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "x", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    ).json()["id"]
    r = isolated_db.delete(
        f"/api/v1/integrations/webhooks/{wh_id}", headers=workspace_headers
    )
    assert r.status_code == 200
    listing = isolated_db.get("/api/v1/integrations/webhooks", headers=workspace_headers).json()
    assert listing["items"][0]["is_active"] is False


# --------------------------------------------------------------------------- #
# Delivery — end to end against the mock server                                #
# --------------------------------------------------------------------------- #


def test_test_webhook_delivers_and_logs(isolated_db, workspace_headers, mock_http_server):
    create = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "t", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    wh_id = create.json()["id"]
    secret = create.json()["secret"]

    r = isolated_db.post(
        f"/api/v1/integrations/webhooks/{wh_id}/test", headers=workspace_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["status_code"] == 200

    # The mock recorded our POST with the right shape + signature
    assert len(mock_http_server["received"]) == 1
    req = mock_http_server["received"][0]
    assert req["headers"].get("X-Shadowblade-Event") == "webhook_test"
    assert "X-Shadowblade-Signature" in req["headers"]
    body_bytes = req["body"].encode("utf-8")
    assert verify_signature(secret, body_bytes, req["headers"]["X-Shadowblade-Signature"])

    # And a log entry was recorded
    logs = isolated_db.get(
        f"/api/v1/integrations/logs?webhook_id={wh_id}",
        headers=workspace_headers,
    ).json()
    assert len(logs["items"]) == 1
    assert logs["items"][0]["status"] == "success"


def test_webhook_delivery_records_4xx_as_error(
    isolated_db, workspace_headers, mock_http_server
):
    mock_http_server["set_status"](500)
    create = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "fail", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    wh_id = create.json()["id"]
    r = isolated_db.post(
        f"/api/v1/integrations/webhooks/{wh_id}/test", headers=workspace_headers
    )
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert r.json()["status_code"] == 500

    listing = isolated_db.get("/api/v1/integrations/webhooks", headers=workspace_headers).json()
    item = next(x for x in listing["items"] if x["id"] == wh_id)
    assert item["failure_count"] == 1
    assert item["last_status"] == "error"


def test_deliver_webhook_pure_call(mock_http_server):
    """Direct deliver_webhook() call without the FastAPI layer."""

    async def _go():
        result = await deliver_webhook(
            target_url=mock_http_server["url"],
            secret="shh",
            event_type="ping",
            payload={"hello": "world"},
        )
        assert result.ok is True
        assert result.status_code == 200
        assert result.duration_ms >= 0
        # Body is valid JSON containing our payload
        sent = json.loads(result.request_body)
        assert sent["event"] == "ping"
        assert sent["payload"] == {"hello": "world"}

    asyncio.get_event_loop().run_until_complete(_go())


def test_deliver_webhook_timeout(monkeypatch):
    """Targeting a port nothing is listening on raises a clean error result."""

    async def _go():
        result = await deliver_webhook(
            target_url="http://127.0.0.1:1/will-never-listen",
            secret="shh",
            event_type="ping",
            payload={"x": 1},
            timeout_s=0.3,
        )
        assert result.ok is False
        assert result.error is not None

    asyncio.get_event_loop().run_until_complete(_go())


# --------------------------------------------------------------------------- #
# Webhook owner / workspace isolation                                          #
# --------------------------------------------------------------------------- #


def test_webhook_cross_workspace_isolation(isolated_db, mock_http_server):
    create = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "wsA", "target_url": mock_http_server["url"]},
        headers={"X-Workspace-Id": "1"},
    )
    wh_id = create.json()["id"]
    # Wrong workspace can't see the row
    assert (
        isolated_db.get(
            "/api/v1/integrations/webhooks", headers={"X-Workspace-Id": "2"}
        ).json()["items"]
        == []
    )
    # Wrong workspace can't fire the test
    r = isolated_db.post(
        f"/api/v1/integrations/webhooks/{wh_id}/test",
        headers={"X-Workspace-Id": "2"},
    )
    assert r.status_code == 404
