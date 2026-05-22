"""Adapters for third-party connectors (Slack, Discord, Notion, Zapier...).

Each adapter is a small object that owns:

* a ``slug`` matching the value stored in
  :class:`app.models.integration.ThirdPartyIntegration.provider`;
* a ``deliver(event_type, payload, config)`` coroutine that POSTs to the
  remote service and returns a
  :class:`app.services.integrations.webhook_service.WebhookDeliveryResult`
  so the audit log treats all transports the same.

The registry at the bottom of this module is the single source of truth
for what we support. Adding ``Trello`` means:

1. write a ``TrelloAdapter`` class here;
2. add its slug to :data:`SUPPORTED_PROVIDERS` in
   :mod:`app.schemas.integration`;
3. extend :data:`PROVIDER_CATALOG` for the discovery endpoint.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.integrations.webhook_service import WebhookDeliveryResult

log = logging.getLogger("shadowblade.integrations.providers")

_DEFAULT_TIMEOUT_S = 8.0


class UnsupportedProviderError(RuntimeError):
    """Raised when an adapter refuses a config it cannot satisfy."""


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _BaseAdapter:
    """Common scaffolding — concrete adapters override ``deliver``."""

    slug: str
    label: str

    async def deliver(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> WebhookDeliveryResult:  # pragma: no cover — abstract
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_summary(event_type: str, payload: dict[str, Any]) -> str:
    """Render a one-line human summary used by chat-style integrations."""
    name_bits: list[str] = [f"[{event_type}]"]
    if "project_id" in payload:
        name_bits.append(f"project={payload['project_id']}")
    if "output_path" in payload:
        name_bits.append(f"output={payload['output_path']}")
    if "title" in payload:
        name_bits.append(f"title={payload['title']!r}")
    if "name" in payload and "project_id" not in payload:
        name_bits.append(f"name={payload['name']!r}")
    return " ".join(name_bits)


async def _post_json(
    url: str,
    *,
    body: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> WebhookDeliveryResult:
    """Shared POST helper. Mirrors the bookkeeping of ``deliver_webhook``."""
    request_body = json.dumps(body, ensure_ascii=False)
    start = time.perf_counter()
    status_code: int | None = None
    response_excerpt: str | None = None
    error: str | None = None
    ok = False
    try:
        async with httpx.AsyncClient(
            timeout=timeout_s, follow_redirects=False
        ) as client:
            response = await client.post(
                url,
                content=request_body.encode("utf-8"),
                headers={"Content-Type": "application/json", **(headers or {})},
            )
            status_code = response.status_code
            text = response.text or ""
            response_excerpt = text if len(text) <= 8192 else text[:8192]
            ok = 200 <= status_code < 300
            if not ok:
                error = f"non-2xx response: {status_code}"
    except httpx.TimeoutException as exc:
        error = f"timeout after {timeout_s:.1f}s: {exc!r}"
    except httpx.HTTPError as exc:
        error = f"http error: {exc!r}"
    except Exception as exc:  # noqa: BLE001
        error = f"unexpected error: {exc!r}"
    duration_ms = int((time.perf_counter() - start) * 1000)
    return WebhookDeliveryResult(
        ok=ok,
        status_code=status_code,
        duration_ms=duration_ms,
        response_excerpt=response_excerpt,
        error=error,
        request_body=request_body,
        delivery_id="provider-" + str(int(time.time() * 1000)),
    )


# ---------------------------------------------------------------------------
# Concrete adapters
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SlackAdapter(_BaseAdapter):
    slug: str = "slack"
    label: str = "Slack"

    async def deliver(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> WebhookDeliveryResult:
        url = config.get("webhook_url") or config.get("url")
        if not url:
            raise UnsupportedProviderError(
                "Slack config requires 'webhook_url' (https://hooks.slack.com/...)"
            )
        body = {
            "text": _format_summary(event_type, payload),
            "attachments": [
                {
                    "color": "#22D3B7",
                    "fields": [
                        {"title": "Event", "value": event_type, "short": True},
                        {
                            "title": "Workspace",
                            "value": str(payload.get("workspace_id", "-")),
                            "short": True,
                        },
                    ],
                    "footer": "ShadowBlade",
                }
            ],
        }
        return await _post_json(url, body=body)


@dataclass(slots=True)
class DiscordAdapter(_BaseAdapter):
    slug: str = "discord"
    label: str = "Discord"

    async def deliver(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> WebhookDeliveryResult:
        url = config.get("webhook_url") or config.get("url")
        if not url:
            raise UnsupportedProviderError(
                "Discord config requires 'webhook_url' (https://discord.com/api/webhooks/...)"
            )
        body = {
            "content": _format_summary(event_type, payload),
            "embeds": [
                {
                    "title": event_type,
                    "description": _format_summary(event_type, payload),
                    "color": 2281911,  # #22D3B7
                }
            ],
        }
        return await _post_json(url, body=body)


@dataclass(slots=True)
class ZapierAdapter(_BaseAdapter):
    slug: str = "zapier"
    label: str = "Zapier"

    async def deliver(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> WebhookDeliveryResult:
        url = config.get("catch_url") or config.get("url") or config.get("webhook_url")
        if not url:
            raise UnsupportedProviderError(
                "Zapier config requires 'catch_url' (https://hooks.zapier.com/hooks/catch/...)"
            )
        body = {"event": event_type, "payload": payload}
        return await _post_json(url, body=body)


@dataclass(slots=True)
class NotionAdapter(_BaseAdapter):
    slug: str = "notion"
    label: str = "Notion"

    async def deliver(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> WebhookDeliveryResult:
        token = config.get("token") or config.get("integration_token")
        database_id = config.get("database_id")
        if not token or not database_id:
            raise UnsupportedProviderError(
                "Notion config requires both 'token' and 'database_id'."
            )
        url = "https://api.notion.com/v1/pages"
        body = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {
                    "title": [
                        {"text": {"content": _format_summary(event_type, payload)}}
                    ]
                },
                "Event": {"rich_text": [{"text": {"content": event_type}}]},
            },
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
        }
        return await _post_json(url, body=body, headers=headers)


@dataclass(slots=True)
class GenericWebhookAdapter(_BaseAdapter):
    slug: str = "generic_webhook"
    label: str = "Generic Webhook"

    async def deliver(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        config: dict[str, Any],
    ) -> WebhookDeliveryResult:
        url = config.get("url") or config.get("webhook_url")
        if not url:
            raise UnsupportedProviderError(
                "Generic webhook config requires 'url'."
            )
        body = {"event": event_type, "payload": payload}
        headers = {k: str(v) for k, v in (config.get("headers") or {}).items()}
        return await _post_json(url, body=body, headers=headers)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


PROVIDER_REGISTRY: dict[str, _BaseAdapter] = {
    "slack": SlackAdapter(),
    "discord": DiscordAdapter(),
    "zapier": ZapierAdapter(),
    "notion": NotionAdapter(),
    "generic_webhook": GenericWebhookAdapter(),
}


def get_provider(slug: str) -> _BaseAdapter:
    """Return the adapter for ``slug`` or raise :class:`UnsupportedProviderError`."""
    try:
        return PROVIDER_REGISTRY[slug]
    except KeyError as exc:
        raise UnsupportedProviderError(f"unknown provider: {slug!r}") from exc


__all__ = [
    "DiscordAdapter",
    "GenericWebhookAdapter",
    "NotionAdapter",
    "PROVIDER_REGISTRY",
    "SlackAdapter",
    "UnsupportedProviderError",
    "ZapierAdapter",
    "get_provider",
]
