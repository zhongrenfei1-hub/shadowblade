"""Integrations service layer — API keys, webhooks, third-party connectors.

This package exposes the moving parts that the REST routers in
:mod:`app.api.integrations` and the event-emitting hooks in
``mix-video`` / ``brand-kits`` / ``templates`` rely on:

* :mod:`.api_key_service` — generate, hash, verify, and revoke API keys
* :mod:`.webhook_service` — sign + deliver outbound webhooks, log results
* :mod:`.providers`       — thin adapters for Slack / Discord / etc.
* :mod:`.events`          — single ``emit_event`` entry point that fans
  events out to every active webhook + third-party integration

Nothing in here imports from :mod:`app.api`, which keeps the import graph
acyclic — routers depend on services, never the other way round.
"""

from app.services.integrations.api_key_service import (
    APIKeyAuthError,
    APIKeyAuthResult,
    generate_api_key,
    hash_api_key,
    mask_api_key,
    require_scope,
    verify_api_key,
)
from app.services.integrations.events import emit_event
from app.services.integrations.webhook_service import (
    WebhookDeliveryResult,
    deliver_webhook,
    sign_payload,
)

__all__ = [
    "APIKeyAuthError",
    "APIKeyAuthResult",
    "WebhookDeliveryResult",
    "deliver_webhook",
    "emit_event",
    "generate_api_key",
    "hash_api_key",
    "mask_api_key",
    "require_scope",
    "sign_payload",
    "verify_api_key",
]
