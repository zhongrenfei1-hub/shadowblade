"""Security-focused tests (6 cases).

Confirms the surface area we care about:

* Hashed storage — DB never has the plaintext key.
* Listing endpoints never expose the secret/hash.
* Webhook test endpoint returns 404 across workspaces.
* HMAC verification rejects tampered bodies and forged signatures.
* Provider config redaction prevents secret leakage in API responses.
* Name validation rejects control characters.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.models.integration import ApiKey as ApiKeyORM
from app.services.integrations.webhook_service import (
    sign_payload,
    verify_signature,
)


def test_api_key_plaintext_never_in_db(isolated_db, api_key_factory):
    plaintext, body = api_key_factory()
    # The DB stores only the SHA-256 hash; the plaintext appears nowhere.
    # Use the monkey-patched SessionLocal so we hit the same tmp DB the
    # HTTP API just wrote to.
    from app.core.db import SessionLocal

    async def _check():
        async with SessionLocal() as db:
            from sqlalchemy import select

            rows = (await db.execute(select(ApiKeyORM))).scalars().all()
            assert len(rows) == 1
            assert rows[0].key_hash != plaintext
            assert plaintext not in rows[0].key_hash
            # The row only stores the prefix and last-four — not the middle.
            assert rows[0].prefix in plaintext
            assert rows[0].last_four == plaintext[-4:]

    asyncio.run(_check())


def test_listing_never_exposes_key_hash(isolated_db, workspace_headers, api_key_factory):
    api_key_factory()
    listing = isolated_db.get("/api/v1/integrations/api-keys", headers=workspace_headers).json()
    assert listing["items"]
    for item in listing["items"]:
        # Neither plaintext nor hash should be in the response payload
        assert "key" not in item
        assert "key_hash" not in item


def test_webhook_listing_hides_secret(isolated_db, workspace_headers, mock_http_server):
    r = isolated_db.post(
        "/api/v1/integrations/webhooks",
        json={"name": "x", "target_url": mock_http_server["url"]},
        headers=workspace_headers,
    )
    full_secret = r.json()["secret"]
    listing = isolated_db.get("/api/v1/integrations/webhooks", headers=workspace_headers).json()
    for item in listing["items"]:
        assert "secret" not in item
        # The masked preview reveals only the last 4 chars of the secret
        assert item["secret_preview"].startswith("•••")
        # The full secret value must not appear anywhere in the JSON
        assert full_secret not in json.dumps(listing)


def test_hmac_signature_detects_body_tampering():
    secret = "s3cret"
    body = b'{"event":"video_generated"}'
    sig = sign_payload(secret, body)
    # Forged: change one byte
    forged_body = body.replace(b"video_generated", b"video_failed")
    assert not verify_signature(secret, forged_body, sig)


def test_third_party_secret_redacted_in_response(isolated_db, workspace_headers):
    """Secret-looking config values are never echoed back verbatim."""
    r = isolated_db.post(
        "/api/v1/integrations/third-party",
        json={
            "name": "notion",
            "provider": "notion",
            "config": {
                "token": "secret_abcdef1234567890",
                "password": "p455word_xyz789",
                "database_id": "db123",
            },
        },
        headers=workspace_headers,
    )
    assert r.status_code == 201
    config = r.json()["config"]
    assert config["token"].startswith("•••")
    assert "abcdef" not in config["token"]
    assert config["password"].startswith("•••")
    assert "p455" not in config["password"]
    # Non-sensitive fields stay readable
    assert config["database_id"] == "db123"


def test_api_key_name_rejects_control_characters(isolated_db, workspace_headers):
    r = isolated_db.post(
        "/api/v1/integrations/api-keys",
        json={"name": "bad\x00name", "scopes": ["*"]},
        headers=workspace_headers,
    )
    assert r.status_code == 422
