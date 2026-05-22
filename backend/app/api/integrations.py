"""REST endpoints for the Integrations module.

Three families share one :class:`APIRouter` (prefix ``/integrations``):

* **API Keys**
    - ``GET    /api/v1/integrations/api-keys``           list
    - ``POST   /api/v1/integrations/api-keys``           generate
    - ``GET    /api/v1/integrations/api-keys/{key_id}``  detail (masked)
    - ``PATCH  /api/v1/integrations/api-keys/{key_id}``  rename / toggle
    - ``DELETE /api/v1/integrations/api-keys/{key_id}``  revoke (soft)

* **Webhooks**
    - ``GET    /api/v1/integrations/webhooks``           list
    - ``POST   /api/v1/integrations/webhooks``           create
    - ``PUT    /api/v1/integrations/webhooks/{id}``      update
    - ``DELETE /api/v1/integrations/webhooks/{id}``      delete (soft)
    - ``POST   /api/v1/integrations/webhooks/{id}/test`` fire test payload

* **Third-party integrations**
    - ``GET    /api/v1/integrations/providers``                    catalog
    - ``GET    /api/v1/integrations/third-party``                  list
    - ``POST   /api/v1/integrations/third-party``                  create
    - ``PUT    /api/v1/integrations/third-party/{id}``             update
    - ``DELETE /api/v1/integrations/third-party/{id}``             delete

* **Logs / overview**
    - ``GET    /api/v1/integrations/logs``                         recent events
    - ``GET    /api/v1/integrations/overview``                     dashboard widget

All endpoints are workspace-scoped via ``X-Workspace-Id`` and follow the
soft-delete convention used by Brand Kits — flip ``is_active=False``,
never DELETE rows that may be referenced by historic render jobs.
"""

from __future__ import annotations

import logging
import secrets as py_secrets
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user_id,
    get_current_workspace_id,
    get_db,
)
from app.models.integration import (
    ApiKey as ApiKeyORM,
    IntegrationLog as IntegrationLogORM,
    ThirdPartyIntegration as ThirdPartyORM,
    Webhook as WebhookORM,
)
from app.schemas.integration import (
    PROVIDER_CATALOG,
    SUPPORTED_PROVIDERS,
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    ApiKeyUpdate,
    IntegrationLogRead,
    IntegrationsOverview,
    ProviderInfo,
    ProviderListResponse,
    ThirdPartyIntegrationCreate,
    ThirdPartyIntegrationRead,
    ThirdPartyIntegrationUpdate,
    WebhookCreate,
    WebhookCreated,
    WebhookRead,
    WebhookTestResult,
    WebhookUpdate,
)
from app.services.integrations.api_key_service import (
    generate_api_key,
    mask_api_key,
)
from app.services.integrations.events import emit_event
from app.services.integrations.webhook_service import deliver_webhook

log = logging.getLogger("shadowblade.api.integrations")
router = APIRouter(prefix="/integrations", tags=["integrations"])


# ---------------------------------------------------------------------------
# Internal helpers — serialization
# ---------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _serialize_api_key(row: ApiKeyORM, *, plaintext: str | None = None) -> dict[str, Any]:
    """ORM → JSON-safe dict. Includes ``key`` only when explicitly passed.

    The plaintext is folded in by the create endpoint exactly once and is
    omitted everywhere else.
    """
    base = {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "owner_id": row.owner_id,
        "name": row.name,
        "prefix": row.prefix,
        "last_four": row.last_four,
        "masked": mask_api_key(row.prefix, row.last_four),
        "scopes": list(row.scopes or []),
        "is_active": bool(row.is_active),
        "last_used_at": _iso(row.last_used_at),
        "expires_at": _iso(row.expires_at),
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }
    if plaintext is not None:
        base["key"] = plaintext
    return base


def _serialize_webhook(
    row: WebhookORM, *, plaintext_secret: str | None = None
) -> dict[str, Any]:
    secret_preview = ""
    if row.secret:
        secret_preview = "•••" + row.secret[-4:] if len(row.secret) >= 4 else "•••"
    base = {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "owner_id": row.owner_id,
        "name": row.name,
        "target_url": row.target_url,
        "event_types": list(row.event_types or []),
        "is_active": bool(row.is_active),
        "last_triggered_at": _iso(row.last_triggered_at),
        "last_status": row.last_status,
        "failure_count": row.failure_count or 0,
        "secret_preview": secret_preview,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }
    if plaintext_secret is not None:
        base["secret"] = plaintext_secret
    return base


def _serialize_third_party(row: ThirdPartyORM) -> dict[str, Any]:
    # Strip obvious secret-looking keys from the config returned to the API.
    # We keep the full config in the DB but redact common credential fields
    # before sending them over the wire — defence in depth in case the UI
    # accidentally renders the response in logs.
    safe_config: dict[str, Any] = {}
    SENSITIVE = {"token", "secret", "password", "access_token", "refresh_token"}
    for k, v in (row.config_json or {}).items():
        if k.lower() in SENSITIVE and isinstance(v, str) and v:
            safe_config[k] = "•••" + v[-4:] if len(v) >= 4 else "•••"
        else:
            safe_config[k] = v
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "owner_id": row.owner_id,
        "name": row.name,
        "provider": row.provider,
        "description": row.description,
        "config": safe_config,
        "event_types": list(row.event_types or []),
        "is_active": bool(row.is_active),
        "last_triggered_at": _iso(row.last_triggered_at),
        "last_status": row.last_status,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _serialize_log(row: IntegrationLogORM) -> dict[str, Any]:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "webhook_id": row.webhook_id,
        "third_party_integration_id": row.third_party_integration_id,
        "api_key_id": row.api_key_id,
        "kind": row.kind,
        "event_type": row.event_type,
        "status": row.status,
        "status_code": row.status_code,
        "duration_ms": row.duration_ms,
        "request_body": row.request_body,
        "response_body": row.response_body,
        "error_message": row.error_message,
        "created_at": _iso(row.created_at),
    }


def _parse_expires(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        # Accept Z-suffixed ISO strings ('2026-06-01T00:00:00Z') by
        # rewriting them into the +00:00 form Python's fromisoformat
        # parses natively across all 3.11+ builds.
        s = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"expires_at is not a valid ISO datetime: {exc}"
        ) from exc
    if dt.tzinfo is not None:
        # Store naive UTC to match the rest of the DB (DateTime, not
        # DateTime(timezone=True)).
        dt = dt.replace(tzinfo=None)
    return dt


# ===========================================================================
# API KEYS
# ===========================================================================


@router.get("/api-keys")
async def list_api_keys(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """List every API key in the caller's workspace (masked)."""
    stmt = (
        select(ApiKeyORM)
        .where(ApiKeyORM.workspace_id == workspace_id)
        .order_by(ApiKeyORM.id.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_api_key(r) for r in rows]}


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Mint a fresh API key. Plaintext is returned exactly once."""
    plaintext, prefix, last_four, key_hash = generate_api_key()
    expires_at = _parse_expires(payload.expires_at)

    row = ApiKeyORM(
        workspace_id=workspace_id,
        owner_id=user_id,
        name=payload.name,
        prefix=prefix,
        last_four=last_four,
        key_hash=key_hash,
        scopes=list(payload.scopes),
        is_active=True,
        expires_at=expires_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    # Emit a non-blocking event so subscribed webhooks see the change.
    try:
        await emit_event(
            workspace_id=workspace_id,
            event_type="api_key_created",
            payload={"api_key_id": row.id, "name": row.name, "workspace_id": workspace_id},
            db=db,
        )
    except Exception:  # noqa: BLE001
        log.exception("emit api_key_created failed for id=%s", row.id)

    log.info(
        "api-key created id=%s workspace=%s prefix=%s scopes=%s",
        row.id,
        workspace_id,
        prefix,
        list(row.scopes or []),
    )
    return _serialize_api_key(row, plaintext=plaintext)


@router.get("/api-keys/{key_id}", response_model=ApiKeyRead)
async def get_api_key(
    key_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Return one API key (masked)."""
    stmt = select(ApiKeyORM).where(
        ApiKeyORM.id == key_id, ApiKeyORM.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="api key not found")
    return _serialize_api_key(row)


@router.patch("/api-keys/{key_id}", response_model=ApiKeyRead)
async def update_api_key(
    key_id: int,
    payload: ApiKeyUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Rename or toggle ``is_active``. Scopes are immutable by design."""
    stmt = select(ApiKeyORM).where(
        ApiKeyORM.id == key_id, ApiKeyORM.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="api key not found")

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return _serialize_api_key(row)

    for key, value in patch.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    log.info("api-key updated id=%s keys=%s", row.id, list(patch))
    return _serialize_api_key(row)


@router.delete("/api-keys/{key_id}", status_code=200)
async def revoke_api_key(
    key_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Soft-revoke. The key remains in the DB but verification rejects it."""
    stmt = select(ApiKeyORM).where(
        ApiKeyORM.id == key_id, ApiKeyORM.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="api key not found")
    if not row.is_active:
        return {"ok": True, "id": key_id, "is_active": False, "already_revoked": True}
    row.is_active = False
    await db.commit()

    try:
        await emit_event(
            workspace_id=workspace_id,
            event_type="api_key_revoked",
            payload={"api_key_id": row.id, "name": row.name, "workspace_id": workspace_id},
            db=db,
        )
    except Exception:  # noqa: BLE001
        log.exception("emit api_key_revoked failed for id=%s", row.id)

    log.info("api-key revoked id=%s workspace=%s", row.id, workspace_id)
    return {"ok": True, "id": key_id, "is_active": False}


# ===========================================================================
# WEBHOOKS
# ===========================================================================


@router.get("/webhooks")
async def list_webhooks(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    stmt = (
        select(WebhookORM)
        .where(WebhookORM.workspace_id == workspace_id)
        .order_by(WebhookORM.id.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_webhook(r) for r in rows]}


@router.post("/webhooks", response_model=WebhookCreated, status_code=201)
async def create_webhook(
    payload: WebhookCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    """Create a new outbound webhook. Returns the full HMAC secret once."""
    secret = payload.secret.strip() if payload.secret else py_secrets.token_urlsafe(32)
    row = WebhookORM(
        workspace_id=workspace_id,
        owner_id=user_id,
        name=payload.name,
        target_url=str(payload.target_url),
        secret=secret,
        event_types=list(payload.event_types or []),
        is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    log.info(
        "webhook created id=%s workspace=%s target=%s events=%s",
        row.id,
        workspace_id,
        row.target_url,
        list(row.event_types or []),
    )
    return _serialize_webhook(row, plaintext_secret=secret)


@router.put("/webhooks/{webhook_id}", response_model=WebhookRead)
async def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    stmt = select(WebhookORM).where(
        WebhookORM.id == webhook_id, WebhookORM.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="webhook not found")

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return _serialize_webhook(row)

    # HttpUrl serializes as Url object → coerce to str when present.
    if "target_url" in patch and patch["target_url"] is not None:
        patch["target_url"] = str(patch["target_url"])

    for key, value in patch.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    log.info("webhook updated id=%s keys=%s", row.id, list(patch))
    return _serialize_webhook(row)


@router.delete("/webhooks/{webhook_id}", status_code=200)
async def delete_webhook(
    webhook_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Soft-delete. Audit logs referencing this webhook keep their FK."""
    stmt = select(WebhookORM).where(
        WebhookORM.id == webhook_id, WebhookORM.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="webhook not found")
    row.is_active = False
    await db.commit()
    log.info("webhook revoked id=%s workspace=%s", row.id, workspace_id)
    return {"ok": True, "id": webhook_id, "is_active": False}


@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResult)
async def test_webhook(
    webhook_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Fire a synthetic ``webhook_test`` payload at the configured URL.

    Useful right after creation — the UI's "Send test" button hits this.
    The result is also persisted to :class:`IntegrationLog` so the user
    can see it in the recent-events drawer.
    """
    stmt = select(WebhookORM).where(
        WebhookORM.id == webhook_id, WebhookORM.workspace_id == workspace_id
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="webhook not found")

    payload = {
        "test": True,
        "workspace_id": workspace_id,
        "webhook_id": webhook_id,
        "message": "Hello from ShadowBlade — this is a test event.",
    }
    result = await deliver_webhook(
        target_url=row.target_url,
        secret=row.secret,
        event_type="webhook_test",
        payload=payload,
    )

    # Update the webhook health counters + log.
    row.last_triggered_at = datetime.utcnow()
    row.last_status = "success" if result.ok else "error"
    if result.ok:
        row.failure_count = 0
    else:
        row.failure_count = (row.failure_count or 0) + 1
    db.add(
        IntegrationLogORM(
            workspace_id=workspace_id,
            webhook_id=webhook_id,
            kind="webhook",
            event_type="webhook_test",
            status="success" if result.ok else "error",
            status_code=result.status_code,
            duration_ms=result.duration_ms,
            request_body=result.request_body[:8192],
            response_body=(result.response_excerpt or "")[:8192],
            error_message=(result.error or None) and result.error[:1024],
        )
    )
    await db.commit()

    return WebhookTestResult(
        ok=result.ok,
        status_code=result.status_code,
        duration_ms=result.duration_ms,
        response_excerpt=result.response_excerpt,
        error=result.error,
    )


# ===========================================================================
# THIRD-PARTY INTEGRATIONS
# ===========================================================================


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers():
    """Static catalog of supported third-party connectors."""
    items = [ProviderInfo(**p) for p in PROVIDER_CATALOG]
    return ProviderListResponse(items=items)


@router.get("/third-party")
async def list_third_party(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    stmt = (
        select(ThirdPartyORM)
        .where(ThirdPartyORM.workspace_id == workspace_id)
        .order_by(ThirdPartyORM.id.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_third_party(r) for r in rows]}


@router.post("/third-party", response_model=ThirdPartyIntegrationRead, status_code=201)
async def create_third_party(
    payload: ThirdPartyIntegrationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    if payload.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported provider: {payload.provider}",
        )
    row = ThirdPartyORM(
        workspace_id=workspace_id,
        owner_id=user_id,
        name=payload.name,
        provider=payload.provider,
        description=payload.description,
        config_json=dict(payload.config or {}),
        event_types=list(payload.event_types or []),
        is_active=True,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    log.info(
        "third-party created id=%s workspace=%s provider=%s",
        row.id,
        workspace_id,
        payload.provider,
    )
    return _serialize_third_party(row)


@router.put("/third-party/{integration_id}", response_model=ThirdPartyIntegrationRead)
async def update_third_party(
    integration_id: int,
    payload: ThirdPartyIntegrationUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    stmt = select(ThirdPartyORM).where(
        ThirdPartyORM.id == integration_id,
        ThirdPartyORM.workspace_id == workspace_id,
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="integration not found")

    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        return _serialize_third_party(row)
    # Rename the field for the ORM (schema uses "config", ORM uses "config_json").
    if "config" in patch:
        patch["config_json"] = patch.pop("config")
    for key, value in patch.items():
        setattr(row, key, value)
    await db.commit()
    await db.refresh(row)
    log.info("third-party updated id=%s keys=%s", row.id, list(patch))
    return _serialize_third_party(row)


@router.delete("/third-party/{integration_id}", status_code=200)
async def delete_third_party(
    integration_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    stmt = select(ThirdPartyORM).where(
        ThirdPartyORM.id == integration_id,
        ThirdPartyORM.workspace_id == workspace_id,
    )
    row = (await db.execute(stmt)).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="integration not found")
    row.is_active = False
    await db.commit()
    return {"ok": True, "id": integration_id, "is_active": False}


# ===========================================================================
# LOGS / OVERVIEW
# ===========================================================================


@router.get("/logs")
async def list_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    limit: int = Query(default=50, ge=1, le=500),
    webhook_id: int | None = Query(default=None),
    third_party_integration_id: int | None = Query(default=None),
    api_key_id: int | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    stmt = (
        select(IntegrationLogORM)
        .where(IntegrationLogORM.workspace_id == workspace_id)
        .order_by(desc(IntegrationLogORM.id))
        .limit(limit)
    )
    if webhook_id is not None:
        stmt = stmt.where(IntegrationLogORM.webhook_id == webhook_id)
    if third_party_integration_id is not None:
        stmt = stmt.where(
            IntegrationLogORM.third_party_integration_id == third_party_integration_id
        )
    if api_key_id is not None:
        stmt = stmt.where(IntegrationLogORM.api_key_id == api_key_id)
    if event_type is not None:
        stmt = stmt.where(IntegrationLogORM.event_type == event_type)
    if status is not None:
        stmt = stmt.where(IntegrationLogORM.status == status)

    rows = (await db.execute(stmt)).scalars().all()
    return {"items": [_serialize_log(r) for r in rows]}


@router.get("/overview")
async def integration_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
):
    """Aggregate snapshot for the dashboard card."""

    async def _count(model, *, active: bool | None = None) -> int:
        stmt = select(func.count(model.id)).where(model.workspace_id == workspace_id)
        if active is True:
            stmt = stmt.where(model.is_active.is_(True))
        elif active is False:
            stmt = stmt.where(model.is_active.is_(False))
        result = (await db.execute(stmt)).scalar()
        return int(result or 0)

    recent_stmt = (
        select(IntegrationLogORM)
        .where(IntegrationLogORM.workspace_id == workspace_id)
        .order_by(desc(IntegrationLogORM.id))
        .limit(10)
    )
    recent_rows = (await db.execute(recent_stmt)).scalars().all()

    body = {
        "api_keys_active": await _count(ApiKeyORM, active=True),
        "api_keys_total": await _count(ApiKeyORM),
        "webhooks_active": await _count(WebhookORM, active=True),
        "webhooks_total": await _count(WebhookORM),
        "third_party_active": await _count(ThirdPartyORM, active=True),
        "third_party_total": await _count(ThirdPartyORM),
        "recent_events": [_serialize_log(r) for r in recent_rows],
    }
    return body


# ===========================================================================
# Manual event emit (for the "Send test event" button in the UI)
# ===========================================================================


@router.post("/events/emit")
async def emit_manual_event(
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    event_type: str = Query(...),
    payload: dict[str, Any] | None = None,
):
    """Manually fire ``event_type`` to every subscriber in the workspace.

    Intended for debugging webhooks/integrations from the UI — not the
    canonical way features should publish events (they go through
    :func:`emit_event` directly).
    """
    await emit_event(
        workspace_id=workspace_id,
        event_type=event_type,
        payload=payload or {"manual": True, "workspace_id": workspace_id},
        db=db,
    )
    return {"ok": True, "event_type": event_type, "workspace_id": workspace_id}


__all__ = ["router"]
