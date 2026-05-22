"""Event dispatcher — the seam between feature code and integrations.

Any feature that wants to notify the outside world calls
:func:`emit_event` with ``(workspace_id, event_type, payload)``. We then
do a single DB lookup for every active Webhook / ThirdPartyIntegration in
that workspace whose ``event_types`` matches (empty list = subscribe to
everything) and schedule the outbound delivery on the FastAPI
``BackgroundTasks`` queue if one is provided; otherwise we fire-and-
forget via ``asyncio.create_task``.

The contract is intentionally tiny so feature code doesn't have to know
which transports are configured. Adding a new transport (e.g. SSE, in-
app inbox) means extending :func:`_dispatch_one` in this file, not
changing every caller.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.models.integration import (
    IntegrationLog,
    ThirdPartyIntegration,
    Webhook,
)
from app.services.integrations.providers import (
    PROVIDER_REGISTRY,
    UnsupportedProviderError,
)
from app.services.integrations.webhook_service import deliver_and_log

log = logging.getLogger("shadowblade.integrations.events")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


async def _find_matching_webhooks(
    db: AsyncSession, *, workspace_id: int, event_type: str
) -> list[Webhook]:
    stmt = select(Webhook).where(
        Webhook.workspace_id == workspace_id,
        Webhook.is_active.is_(True),
    )
    rows: list[Webhook] = list((await db.execute(stmt)).scalars().all())
    return [
        w
        for w in rows
        if not w.event_types or event_type in (w.event_types or [])
    ]


async def _find_matching_third_party(
    db: AsyncSession, *, workspace_id: int, event_type: str
) -> list[ThirdPartyIntegration]:
    stmt = select(ThirdPartyIntegration).where(
        ThirdPartyIntegration.workspace_id == workspace_id,
        ThirdPartyIntegration.is_active.is_(True),
    )
    rows: list[ThirdPartyIntegration] = list((await db.execute(stmt)).scalars().all())
    return [
        i
        for i in rows
        if not i.event_types or event_type in (i.event_types or [])
    ]


# ---------------------------------------------------------------------------
# Dispatchers
# ---------------------------------------------------------------------------


async def _dispatch_one(
    db: AsyncSession,
    *,
    workspace_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Fan one event out to every active subscriber in the workspace.

    The session passed in is owned by the caller — we use it for both the
    discovery queries and the audit-log writes so the whole dispatch is
    visible inside a single SQL transaction when the caller commits.
    """
    webhooks = await _find_matching_webhooks(
        db, workspace_id=workspace_id, event_type=event_type
    )
    third_party = await _find_matching_third_party(
        db, workspace_id=workspace_id, event_type=event_type
    )

    if not webhooks and not third_party:
        log.debug(
            "no subscribers for event=%s workspace=%s — skipping",
            event_type,
            workspace_id,
        )
        return

    # 1) Generic webhooks
    for wh in webhooks:
        try:
            await deliver_and_log(
                db, webhook=wh, event_type=event_type, payload=payload
            )
        except Exception as exc:  # noqa: BLE001
            log.error(
                "webhook delivery raised for id=%s event=%s: %r",
                wh.id,
                event_type,
                exc,
            )

    # 2) Third-party connectors
    for tp in third_party:
        try:
            adapter = PROVIDER_REGISTRY[tp.provider]
        except KeyError as exc:
            log.error(
                "third_party_integration id=%s declares unknown provider %r",
                tp.id,
                tp.provider,
            )
            db.add(
                IntegrationLog(
                    workspace_id=workspace_id,
                    third_party_integration_id=tp.id,
                    kind="third_party",
                    event_type=event_type,
                    status="error",
                    error_message=f"unknown provider: {tp.provider!r}",
                )
            )
            await db.commit()
            continue
        try:
            result = await adapter.deliver(
                event_type=event_type, payload=payload, config=tp.config_json or {}
            )
            tp.last_status = "success" if result.ok else "error"
            from datetime import datetime as _dt

            tp.last_triggered_at = _dt.utcnow()
            await db.commit()
            db.add(
                IntegrationLog(
                    workspace_id=workspace_id,
                    third_party_integration_id=tp.id,
                    kind="third_party",
                    event_type=event_type,
                    status="success" if result.ok else "error",
                    status_code=result.status_code,
                    duration_ms=result.duration_ms,
                    request_body=result.request_body[:8192],
                    response_body=(result.response_excerpt or "")[:8192],
                    error_message=(result.error or None) and result.error[:1024],
                )
            )
            await db.commit()
        except UnsupportedProviderError as exc:
            log.error("provider %r refused delivery: %r", tp.provider, exc)
        except Exception as exc:  # noqa: BLE001
            log.error(
                "third_party delivery raised for id=%s provider=%s event=%s: %r",
                tp.id,
                tp.provider,
                event_type,
                exc,
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def emit_event(
    *,
    workspace_id: int,
    event_type: str,
    payload: dict[str, Any],
    db: AsyncSession | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    """Fire ``event_type`` to every subscriber in ``workspace_id``.

    Two modes:

    * **Inline** (``background_tasks`` is None and ``db`` is supplied) —
      runs synchronously on the calling coroutine. Used by the
      ``/test`` and ``/emit`` endpoints where the response should reflect
      whether anything actually fired.

    * **Background** (``background_tasks`` supplied) — schedules a fresh
      session + dispatch on FastAPI's per-request background queue so
      the calling endpoint can return immediately. Used by the mix-video
      pipeline because we don't want a slow customer webhook to delay
      the user's task-id response.

    The function is idempotent w.r.t. unknown event types — they still
    write an audit row when a subscriber matches.
    """
    if background_tasks is not None:
        # Capture by value; the background coroutine opens its own session.
        async def _run() -> None:
            async with SessionLocal() as session:
                try:
                    await _dispatch_one(
                        session,
                        workspace_id=workspace_id,
                        event_type=event_type,
                        payload=payload,
                    )
                except Exception:  # noqa: BLE001
                    log.exception(
                        "background emit_event failed event=%s workspace=%s",
                        event_type,
                        workspace_id,
                    )

        background_tasks.add_task(asyncio.run, _run())
        return

    if db is None:
        # No DB and no BG — open a fresh session ourselves. This is the
        # path the tests use because they don't always wire BackgroundTasks.
        async with SessionLocal() as session:
            await _dispatch_one(
                session,
                workspace_id=workspace_id,
                event_type=event_type,
                payload=payload,
            )
        return

    await _dispatch_one(
        db,
        workspace_id=workspace_id,
        event_type=event_type,
        payload=payload,
    )


__all__ = ["emit_event"]
