"""Webhook delivery — HMAC signing, async POST, retries, audit logging.

The dispatcher runs entirely off the request hot path: callers fire
:func:`emit_event` (from :mod:`.events`) which schedules deliveries via
FastAPI ``BackgroundTasks`` — the synchronous endpoint returns the
moment we've persisted the event. The actual HTTP call happens on the
server's thread pool so a slow customer endpoint can't slow down the
mix-video pipeline.

Signing follows the GitHub / Stripe convention: header
``X-Shadowblade-Signature`` carries ``sha256=<hex>`` where the digest is
``HMAC_SHA256(secret, request_body)``. We also include ``X-Shadowblade-
Event`` (the event type), ``X-Shadowblade-Delivery`` (a UUID for
idempotency on the receiver side) and ``X-Shadowblade-Timestamp`` (UNIX
seconds — receivers can reject anything older than ~5 minutes to
foil replay attacks).

The result of every delivery is recorded in
:class:`app.models.integration.IntegrationLog`. That's the single audit
source the UI and the regression tests both read from.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import IntegrationLog, Webhook as WebhookORM

log = logging.getLogger("shadowblade.integrations.webhook")

# Receivers should answer quickly — we treat anything beyond 8 seconds as
# a failure. Production deployments may want to make this a setting.
_DELIVERY_TIMEOUT_S = 8.0
# Cap the request/response body we store in the audit log. Smaller =
# cheaper to ship around and protects us from a payload that mirrors the
# secret accidentally.
_MAX_LOG_BODY = 8192


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WebhookDeliveryResult:
    """The outcome of a single POST. Mirrors what gets written to the log."""

    ok: bool
    status_code: int | None
    duration_ms: int
    response_excerpt: str | None
    error: str | None
    request_body: str
    delivery_id: str


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------


def sign_payload(secret: str, body: bytes) -> str:
    """Return ``sha256=<hex>`` ready to be slotted into the signature header.

    Pure function — kept side-effect free so unit tests can pin the
    canonical output without standing up an HTTP server.
    """
    if not isinstance(secret, str):
        raise TypeError("secret must be str")
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: bytes, provided: str) -> bool:
    """Constant-time comparison of the expected signature against ``provided``.

    Used by integration tests (we sit on both ends of the wire) and
    receivers in the docs/examples.
    """
    expected = sign_payload(secret, body)
    return hmac.compare_digest(expected, provided)


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------


def _truncate(value: str | None, *, limit: int = _MAX_LOG_BODY) -> str | None:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[:limit] + "…[truncated]"


async def _write_log(
    db: AsyncSession,
    *,
    workspace_id: int,
    webhook: WebhookORM | None,
    third_party_integration_id: int | None,
    kind: str,
    event_type: str,
    result: WebhookDeliveryResult,
) -> IntegrationLog:
    """Persist one audit row and return it."""
    row = IntegrationLog(
        workspace_id=workspace_id,
        webhook_id=webhook.id if webhook is not None else None,
        third_party_integration_id=third_party_integration_id,
        kind=kind,
        event_type=event_type,
        status="success" if result.ok else "error",
        status_code=result.status_code,
        duration_ms=result.duration_ms,
        request_body=_truncate(result.request_body),
        response_body=_truncate(result.response_excerpt),
        error_message=_truncate(result.error, limit=1024),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


async def deliver_webhook(
    *,
    target_url: str,
    secret: str,
    event_type: str,
    payload: dict[str, Any],
    timeout_s: float = _DELIVERY_TIMEOUT_S,
    http_client: httpx.AsyncClient | None = None,
) -> WebhookDeliveryResult:
    """POST a signed JSON body to ``target_url`` and report the outcome.

    Pure delivery — no DB writes here so unit tests can call it without a
    session. The caller (:func:`deliver_and_log`) wraps this with the
    audit-log update.
    """
    delivery_id = uuid.uuid4().hex
    timestamp = str(int(time.time()))
    body_bytes = json.dumps(
        {
            "event": event_type,
            "delivery_id": delivery_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "payload": payload,
        },
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ShadowBlade-Webhook/1.0",
        "X-Shadowblade-Event": event_type,
        "X-Shadowblade-Delivery": delivery_id,
        "X-Shadowblade-Timestamp": timestamp,
        "X-Shadowblade-Signature": sign_payload(secret, body_bytes),
    }

    start = time.perf_counter()
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=timeout_s, follow_redirects=False)
    status_code: int | None = None
    response_excerpt: str | None = None
    error: str | None = None
    ok = False
    try:
        response = await client.post(target_url, content=body_bytes, headers=headers)
        status_code = response.status_code
        # Bound the body we copy back for the audit log + UI.
        text = response.text or ""
        response_excerpt = text if len(text) <= _MAX_LOG_BODY else text[:_MAX_LOG_BODY]
        ok = 200 <= response.status_code < 300
        if not ok:
            error = f"non-2xx response: {response.status_code}"
    except httpx.TimeoutException as exc:
        error = f"timeout after {timeout_s:.1f}s: {exc!r}"
    except httpx.HTTPError as exc:
        error = f"http error: {exc!r}"
    except Exception as exc:  # noqa: BLE001 — log everything
        error = f"unexpected error: {exc!r}"
    finally:
        if owns_client:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass

    duration_ms = int((time.perf_counter() - start) * 1000)
    return WebhookDeliveryResult(
        ok=ok,
        status_code=status_code,
        duration_ms=duration_ms,
        response_excerpt=response_excerpt,
        error=error,
        request_body=body_bytes.decode("utf-8"),
        delivery_id=delivery_id,
    )


async def deliver_and_log(
    db: AsyncSession,
    *,
    webhook: WebhookORM,
    event_type: str,
    payload: dict[str, Any],
    http_client: httpx.AsyncClient | None = None,
) -> tuple[WebhookDeliveryResult, IntegrationLog]:
    """Run delivery + persist the audit log + update webhook health counters."""
    result = await deliver_webhook(
        target_url=webhook.target_url,
        secret=webhook.secret,
        event_type=event_type,
        payload=payload,
        http_client=http_client,
    )

    # Update bookkeeping on the Webhook row itself. This is read-after-write
    # safe because the same session owns both the webhook ORM and the new log.
    webhook.last_triggered_at = datetime.utcnow()
    webhook.last_status = "success" if result.ok else "error"
    if result.ok:
        webhook.failure_count = 0
    else:
        webhook.failure_count = (webhook.failure_count or 0) + 1
    await db.commit()
    await db.refresh(webhook)

    log_row = await _write_log(
        db,
        workspace_id=webhook.workspace_id,
        webhook=webhook,
        third_party_integration_id=None,
        kind="webhook",
        event_type=event_type,
        result=result,
    )
    return result, log_row


async def deliver_with_retry(
    db: AsyncSession,
    *,
    webhook: WebhookORM,
    event_type: str,
    payload: dict[str, Any],
    attempts: int = 3,
    backoff_base_s: float = 0.5,
) -> WebhookDeliveryResult:
    """Try ``deliver_and_log`` up to ``attempts`` times with linear backoff.

    Each attempt writes its own audit row, so the UI can see the full
    retry trail. Returns the result of the *last* attempt.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    last: WebhookDeliveryResult | None = None
    for i in range(attempts):
        result, _ = await deliver_and_log(
            db, webhook=webhook, event_type=event_type, payload=payload
        )
        last = result
        if result.ok:
            return result
        if i < attempts - 1:
            await asyncio.sleep(backoff_base_s * (i + 1))
    assert last is not None
    return last


__all__ = [
    "WebhookDeliveryResult",
    "deliver_and_log",
    "deliver_webhook",
    "deliver_with_retry",
    "sign_payload",
    "verify_signature",
]
