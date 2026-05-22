"""Integration ORM — API Keys, Webhooks, third-party connectors, and audit logs.

The integrations module is the public seam between ShadowBlade and the
outside world. It owns four entities:

* :class:`ApiKey` — opaque bearer tokens that let machine clients call
  ``/api/v1/mix-video``, ``/api/v1/templates`` etc. without going through
  the cookie/JWT auth flow. Only the SHA-256 hash and a short prefix are
  ever stored; the plaintext is returned **once** by ``POST /api/v1/
  integrations/api-keys`` and the caller is expected to copy it out.
* :class:`Webhook` — outbound HTTP hooks. The user gives us a URL, a list
  of event types they care about (``video_generated``, ``brand_kit_updated``,
  ...), and an optional ``secret`` used to sign the payload with
  HMAC-SHA256. We POST a JSON body and record the result in
  :class:`IntegrationLog`.
* :class:`ThirdPartyIntegration` — opt-in connectors (Slack, Discord,
  Notion, Zapier). The credentials are encrypted-at-rest as a JSON blob
  in ``config_json``; the model layer is intentionally generic so adding
  a new provider is a registry change, not a migration.
* :class:`IntegrationLog` — append-only audit trail for every webhook
  delivery, third-party push, and key-related event. Keeps just enough
  context for the UI to render a useful "what happened" timeline.

All four tables are workspace-scoped (``workspace_id`` FK + index) so the
team boundary maps cleanly onto multi-tenant deployments. Soft-delete is
the rule everywhere — flip ``is_active=False`` rather than ``DELETE``
because historical render jobs may reference the key/hook by id.

See:
* :mod:`app.schemas.integration` for the validation layer
* :mod:`app.services.integrations` for the auth/webhook/event services
* :mod:`app.api.integrations` for the REST endpoints
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ApiKey(Base):
    """Hashed bearer token. Plaintext is returned exactly once at creation."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- ownership ----------------------------------------------------------
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    # --- presentation -------------------------------------------------------
    # Free-form label the user typed when they generated the key.
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="API Key")
    # First 8 chars of the plaintext, e.g. "sb_live_". Stored so the UI can
    # show "sb_live_•••••abcd" without ever needing the real token.
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # Last 4 chars of the plaintext, for the same UI masking trick.
    last_four: Mapped[str] = mapped_column(String(4), nullable=False, default="")

    # --- secret -------------------------------------------------------------
    # SHA-256 hex digest of the full plaintext. 64 chars.
    key_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    # --- permissions --------------------------------------------------------
    # JSON array of scope strings, e.g. ["mix:read", "mix:write",
    # "templates:read", "brand-kit:read", "*"]. Empty list = no rights.
    scopes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # --- lifecycle ----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    # Optional hard expiry. NULL = never expires.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- timestamps ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Webhook(Base):
    """Outbound webhook subscription — sends signed JSON to a user-owned URL."""

    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- ownership ----------------------------------------------------------
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    # --- destination --------------------------------------------------------
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="Webhook")
    # The full URL we POST to. https:// preferred but http allowed for dev.
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    # HMAC-SHA256 secret. Plaintext is fine here because the value is meant
    # to be read back by the user from the UI (it's *their* secret).
    secret: Mapped[str] = mapped_column(String(128), nullable=False, default="")

    # --- event subscriptions ------------------------------------------------
    # JSON array of event type strings, e.g.
    # ["video_generated", "template_updated", "brand_kit_updated"].
    # An empty list means "fire on every event" (matches GitHub semantics).
    event_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # --- lifecycle ----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    # Updated on the *last* outbound delivery — regardless of success.
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    # 1xx/2xx → "success", 4xx/5xx/timeout → "error". Free-form for
    # forward-compat (we may grow "rate_limited", "disabled_by_remote", ...).
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Count of consecutive failures — used to auto-disable after a threshold.
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # --- timestamps ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ThirdPartyIntegration(Base):
    """Connector to an external service (Slack, Discord, Notion, Zapier...).

    The ``provider`` slug routes the connector to the right adapter inside
    :mod:`app.services.integrations.providers` at delivery time. ``config_json``
    is intentionally a free-form dict because each provider stores wildly
    different things (workspace IDs, channel IDs, OAuth bundles, ...).
    """

    __tablename__ = "third_party_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- ownership ----------------------------------------------------------
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    # --- identity -----------------------------------------------------------
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # "slack" | "discord" | "notion" | "zapier" | "generic_webhook"
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # User-supplied description shown in the integrations grid.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- configuration ------------------------------------------------------
    # Free-form dict (encrypted-at-rest in production deployments).
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Optional event filter; empty array = "fire on every event".
    event_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # --- lifecycle ----------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # --- timestamps ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IntegrationLog(Base):
    """Append-only audit row for every outbound integration call.

    One row per delivery attempt — even retries get their own row so the
    history is faithful. Linked to *either* a Webhook or a
    ThirdPartyIntegration, never both (the foreign keys are nullable to
    accommodate that — exactly one is expected to be non-NULL per row).
    Key-management events (creation/revocation) live in their own rows
    where both FKs are NULL and ``kind`` carries the discriminator.
    """

    __tablename__ = "integration_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # --- scoping ------------------------------------------------------------
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    webhook_id: Mapped[int | None] = mapped_column(
        ForeignKey("webhooks.id"), nullable=True, index=True
    )
    third_party_integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("third_party_integrations.id"), nullable=True, index=True
    )
    api_key_id: Mapped[int | None] = mapped_column(
        ForeignKey("api_keys.id"), nullable=True, index=True
    )

    # --- payload ------------------------------------------------------------
    # "webhook" | "third_party" | "api_key" — disambiguator that the UI
    # uses to pick an icon/colour without having to inspect the FKs.
    kind: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # "success" | "error" | "pending" | "skipped"
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    # HTTP status code (200, 404, ...) for HTTP deliveries; NULL otherwise.
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Wall-clock duration in milliseconds.
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Truncated to keep the audit log small — the schema layer enforces caps.
    request_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- timestamps ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )


__all__ = [
    "ApiKey",
    "IntegrationLog",
    "ThirdPartyIntegration",
    "Webhook",
]
