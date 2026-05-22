"""Integration — Pydantic V2 request/response schemas.

The contract here is the source of truth for both the REST API and the
internal webhook delivery code. We follow the same ``Base / Create /
Update / Read`` layout as :mod:`app.schemas.brand_kit` so the frontend
can predict the shape of every endpoint.

Three families live in this module:

* **API Keys** — :class:`ApiKeyCreate`, :class:`ApiKeyRead`,
  :class:`ApiKeyCreated`. ``ApiKeyCreated`` is special: it includes the
  one-time plaintext ``key`` field and is *only* returned by the create
  endpoint. Subsequent GET/list calls return :class:`ApiKeyRead` which
  exposes the masked prefix/last-four but never the secret.
* **Webhooks** — full CRUD plus :class:`WebhookTestResult` for the
  ``/test`` endpoint.
* **Third-party integrations** — provider-keyed CRUD, with a hand-curated
  registry of supported providers exposed as :data:`SUPPORTED_PROVIDERS`.

Event types are constrained to a documented enum so a typo in the UI
becomes a 422 instead of a silently-ignored subscription.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

# Every event the platform may emit. The mix-video pipeline, brand-kit
# editor, template loader, and key-management API all push through
# :mod:`app.services.integrations.events` and the dispatcher rejects
# anything not on this list — that way we never accidentally drop an
# event the user thought they had subscribed to.
EventType = Literal[
    "video_generated",
    "video_failed",
    "template_updated",
    "brand_kit_updated",
    "api_key_created",
    "api_key_revoked",
    "webhook_test",
    "ping",
]

# The scopes an API key can hold. ``*`` is the wildcard — used by the
# default key the user gets when they first land on the integrations
# page. Each downstream endpoint declares the scope it needs (see
# :mod:`app.services.integrations.api_key_service`).
ApiKeyScope = Literal[
    "*",
    "mix:read",
    "mix:write",
    "templates:read",
    "templates:write",
    "brand-kit:read",
    "brand-kit:write",
    "webhooks:read",
    "webhooks:write",
]

# Third-party providers supported by the connector registry. New providers
# get added here AND in :mod:`app.services.integrations.providers`.
ProviderSlug = Literal[
    "slack",
    "discord",
    "notion",
    "zapier",
    "generic_webhook",
]

SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "slack",
    "discord",
    "notion",
    "zapier",
    "generic_webhook",
)

# Display metadata for the integrations grid. The frontend reads this via
# ``GET /api/v1/integrations/providers``.
PROVIDER_CATALOG: list[dict[str, Any]] = [
    {
        "slug": "slack",
        "label": "Slack",
        "description": "Post render notifications to a Slack channel.",
        "config_hint": "Provide a webhook URL from https://api.slack.com/apps.",
        "supports_test": True,
    },
    {
        "slug": "discord",
        "label": "Discord",
        "description": "Send render summaries to a Discord channel via webhook.",
        "config_hint": "Use a Discord channel Webhook URL.",
        "supports_test": True,
    },
    {
        "slug": "notion",
        "label": "Notion",
        "description": "Append video metadata to a Notion database.",
        "config_hint": "Internal integration token + database ID.",
        "supports_test": False,
    },
    {
        "slug": "zapier",
        "label": "Zapier",
        "description": "Trigger any Zap on completed renders or brand-kit updates.",
        "config_hint": "Zapier catch-hook URL.",
        "supports_test": True,
    },
    {
        "slug": "generic_webhook",
        "label": "Generic Webhook",
        "description": "Plain HTTPS POST with a signed JSON payload.",
        "config_hint": "Any HTTPS endpoint that accepts POST requests.",
        "supports_test": True,
    },
]


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

_NAME_OK = re.compile(r"^[\w\-\. ]{1,120}$", flags=re.UNICODE)


def _normalize_name(raw: str) -> str:
    """Strip and reject names with control chars / pathological lengths."""
    if not isinstance(raw, str):
        raise ValueError("name must be a string")
    value = raw.strip()
    if not value:
        raise ValueError("name must not be empty")
    if len(value) > 120:
        raise ValueError("name too long (max 120 chars)")
    if not _NAME_OK.match(value):
        raise ValueError(
            "name contains invalid characters (letters, digits, spaces, '-', '.', '_' only)"
        )
    return value


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


class ApiKeyBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(default="API Key", min_length=1, max_length=120)
    scopes: list[ApiKeyScope] = Field(
        default_factory=lambda: ["*"],
        description="Scope strings granted to this key. Use ['*'] for full access.",
    )
    expires_at: str | None = Field(
        default=None,
        description="ISO-8601 datetime. None = never expires.",
    )

    @field_validator("name", mode="before")
    @classmethod
    def _name_ok(cls, v: Any) -> str:
        return _normalize_name(v)

    @field_validator("scopes", mode="after")
    @classmethod
    def _dedupe_scopes(cls, v: list[str]) -> list[str]:
        # Deduplicate while preserving order — UX-friendlier than set().
        seen: set[str] = set()
        out: list[str] = []
        for s in v:
            if s not in seen:
                seen.add(s)
                out.append(s)
        if not out:
            raise ValueError("at least one scope is required")
        return out


class ApiKeyCreate(ApiKeyBase):
    """Body shape for ``POST /api/v1/integrations/api-keys``."""


class ApiKeyUpdate(BaseModel):
    """PATCH body — currently only ``name`` and ``is_active`` are mutable.

    Scopes are immutable after creation by design — narrowing a live key's
    permissions can silently break running integrations. Issue a new key
    with the narrower scope and revoke the old one instead.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name_ok(cls, v: Any) -> Any:
        return _normalize_name(v) if v is not None else None


class ApiKeyRead(BaseModel):
    """Masked view returned by GET /api-keys (list and detail)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    workspace_id: int
    owner_id: int | None = None
    name: str
    prefix: str
    last_four: str
    masked: str = Field(
        ...,
        description="Display string like 'sb_live_•••••abcd' for the UI.",
    )
    scopes: list[str]
    is_active: bool
    last_used_at: str | None = None
    expires_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ApiKeyCreated(ApiKeyRead):
    """Returned exactly once from ``POST /api/v1/integrations/api-keys``.

    Carries the **plaintext** ``key`` field that the caller MUST copy
    immediately — every subsequent GET returns the masked view instead.
    """

    key: str = Field(
        ...,
        description="The full plaintext token. Only available at creation time.",
    )


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


class WebhookBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(default="Webhook", min_length=1, max_length=120)
    target_url: HttpUrl
    event_types: list[EventType] = Field(
        default_factory=list,
        description="Event names to fire on. Empty = subscribe to all events.",
    )
    secret: str = Field(
        default="",
        max_length=128,
        description="HMAC-SHA256 shared secret. Empty = generate one server-side.",
    )

    @field_validator("name", mode="before")
    @classmethod
    def _name_ok(cls, v: Any) -> str:
        return _normalize_name(v)

    @field_validator("event_types", mode="after")
    @classmethod
    def _dedupe_events(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for ev in v:
            if ev not in seen:
                seen.add(ev)
                out.append(ev)
        return out


class WebhookCreate(WebhookBase):
    """POST /api/v1/integrations/webhooks."""


class WebhookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    target_url: HttpUrl | None = None
    event_types: list[EventType] | None = None
    secret: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name_ok(cls, v: Any) -> Any:
        return _normalize_name(v) if v is not None else None


class WebhookRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    workspace_id: int
    owner_id: int | None = None
    name: str
    target_url: str
    event_types: list[str]
    is_active: bool
    last_triggered_at: str | None = None
    last_status: str | None = None
    failure_count: int = 0
    # The secret is intentionally NOT included in the list response. It is
    # only shown by ``GET /webhooks/{id}/secret`` (which is gated to the
    # owner) and by the original create response.
    secret_preview: str = Field(
        default="",
        description="Last 4 chars of the secret, e.g. '••••abcd'.",
    )
    created_at: str | None = None
    updated_at: str | None = None


class WebhookCreated(WebhookRead):
    """Returned by POST /webhooks — includes the full secret one time."""

    secret: str = Field(..., description="The full HMAC secret. Copy now.")


class WebhookTestResult(BaseModel):
    """Returned by POST /webhooks/{id}/test."""

    ok: bool
    status_code: int | None = None
    duration_ms: int
    response_excerpt: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Third-party integrations
# ---------------------------------------------------------------------------


class ThirdPartyIntegrationBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=120)
    provider: ProviderSlug
    description: str | None = Field(default=None, max_length=2048)
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific configuration. Shape varies.",
    )
    event_types: list[EventType] = Field(default_factory=list)

    @field_validator("name", mode="before")
    @classmethod
    def _name_ok(cls, v: Any) -> str:
        return _normalize_name(v)

    @field_validator("config", mode="after")
    @classmethod
    def _bound_config_size(cls, v: dict) -> dict:
        # Defence-in-depth — keep the per-integration config blob small.
        # Bigger payloads belong in object storage, not in the API key DB.
        import json

        if len(json.dumps(v, ensure_ascii=False)) > 16 * 1024:
            raise ValueError("config must be smaller than 16KB when serialized")
        return v


class ThirdPartyIntegrationCreate(ThirdPartyIntegrationBase):
    """POST /api/v1/integrations/third-party."""


class ThirdPartyIntegrationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2048)
    config: dict[str, Any] | None = None
    event_types: list[EventType] | None = None
    is_active: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name_ok(cls, v: Any) -> Any:
        return _normalize_name(v) if v is not None else None


class ThirdPartyIntegrationRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    workspace_id: int
    owner_id: int | None = None
    name: str
    provider: str
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    event_types: list[str]
    is_active: bool
    last_triggered_at: str | None = None
    last_status: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------


class IntegrationLogRead(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    workspace_id: int
    webhook_id: int | None = None
    third_party_integration_id: int | None = None
    api_key_id: int | None = None
    kind: str
    event_type: str
    status: str
    status_code: int | None = None
    duration_ms: int | None = None
    request_body: str | None = None
    response_body: str | None = None
    error_message: str | None = None
    created_at: str | None = None


# ---------------------------------------------------------------------------
# Aggregate / discovery responses
# ---------------------------------------------------------------------------


class ProviderInfo(BaseModel):
    slug: str
    label: str
    description: str
    config_hint: str
    supports_test: bool


class ProviderListResponse(BaseModel):
    items: list[ProviderInfo]


class IntegrationsOverview(BaseModel):
    """High-level snapshot used by the integrations dashboard widget."""

    api_keys_active: int
    api_keys_total: int
    webhooks_active: int
    webhooks_total: int
    third_party_active: int
    third_party_total: int
    recent_events: list[IntegrationLogRead]


__all__ = [
    "ApiKeyBase",
    "ApiKeyCreate",
    "ApiKeyCreated",
    "ApiKeyRead",
    "ApiKeyScope",
    "ApiKeyUpdate",
    "EventType",
    "IntegrationLogRead",
    "IntegrationsOverview",
    "PROVIDER_CATALOG",
    "ProviderInfo",
    "ProviderListResponse",
    "ProviderSlug",
    "SUPPORTED_PROVIDERS",
    "ThirdPartyIntegrationBase",
    "ThirdPartyIntegrationCreate",
    "ThirdPartyIntegrationRead",
    "ThirdPartyIntegrationUpdate",
    "WebhookBase",
    "WebhookCreate",
    "WebhookCreated",
    "WebhookRead",
    "WebhookTestResult",
    "WebhookUpdate",
]
