/**
 * Integrations API client — API key + webhook + 第三方集成 + 事件日志。
 *
 * 后端：`/api/v1/integrations/{overview,api-keys,webhooks,third-party,providers,logs}`
 */

export interface ApiKey {
  id: number;
  workspace_id: number;
  name: string;
  prefix: string;
  masked: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  /** 完整 key 仅在创建时返回一次，必须立即保存。 */
  plaintext: string;
}

export interface Webhook {
  id: number;
  workspace_id: number;
  url: string;
  events: string[];
  is_active: boolean;
  secret_masked: string | null;
  last_delivery_at: string | null;
  last_delivery_status: number | null;
  created_at: string;
}

export interface ThirdPartyIntegration {
  id: number;
  workspace_id: number;
  provider_slug: string;
  display_label: string;
  is_active: boolean;
  config_summary: string | null;
  connected_at: string;
}

export interface Provider {
  slug: string;
  label: string;
  description: string;
  config_hint: string;
  supports_test: boolean;
}

export interface IntegrationLog {
  id: number;
  workspace_id: number;
  source: "api_key" | "webhook" | "third_party";
  event_type: string;
  status: "success" | "failed" | "pending";
  message: string;
  created_at: string;
}

export interface IntegrationsOverview {
  api_keys_active: number;
  api_keys_total: number;
  webhooks_active: number;
  webhooks_total: number;
  third_party_active: number;
  third_party_total: number;
  recent_events: IntegrationLog[];
}

const IS_SERVER = typeof window === "undefined";
const SERVER_BASE = process.env.BACKEND_URL || "http://localhost:8000";
const BASE = IS_SERVER
  ? `${SERVER_BASE}/api/v1`
  : process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "/api/v1";

function authHeaders(): Record<string, string> {
  return {
    "X-Workspace-Id": "1",
    "X-User-Id": "1",
  };
}

class IntegrationsApiError extends Error {
  constructor(
    public status: number,
    public path: string,
    message: string,
  ) {
    super(message);
    this.name = "IntegrationsApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const { headers, ...rest } = init;
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    ...rest,
    headers: {
      ...authHeaders(),
      ...(rest.body ? { "content-type": "application/json" } : {}),
      ...headers,
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new IntegrationsApiError(
      res.status,
      path,
      `integrations ${res.status} ${path}: ${detail.slice(0, 300)}`,
    );
  }
  return res.json() as Promise<T>;
}

// ─── overview ─────────────────────────────────────────────────────────

export function getOverview(): Promise<IntegrationsOverview> {
  return request<IntegrationsOverview>("/integrations/overview");
}

// ─── providers ────────────────────────────────────────────────────────

export function listProviders(): Promise<{ items: Provider[] }> {
  return request<{ items: Provider[] }>("/integrations/providers");
}

// ─── API keys ─────────────────────────────────────────────────────────

export function listApiKeys(): Promise<{ items: ApiKey[] }> {
  return request<{ items: ApiKey[] }>("/integrations/api-keys");
}

export function createApiKey(
  name: string,
  scopes: string[],
): Promise<ApiKeyCreated> {
  return request<ApiKeyCreated>("/integrations/api-keys", {
    method: "POST",
    body: JSON.stringify({ name, scopes }),
  });
}

export function revokeApiKey(id: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/integrations/api-keys/${id}`, {
    method: "DELETE",
  });
}

// ─── webhooks ─────────────────────────────────────────────────────────

export function listWebhooks(): Promise<{ items: Webhook[] }> {
  return request<{ items: Webhook[] }>("/integrations/webhooks");
}

export function createWebhook(
  url: string,
  events: string[],
): Promise<Webhook> {
  return request<Webhook>("/integrations/webhooks", {
    method: "POST",
    body: JSON.stringify({ url, events }),
  });
}

export function testWebhook(
  id: number,
): Promise<{ ok: boolean; status_code: number; took_ms: number }> {
  return request<{ ok: boolean; status_code: number; took_ms: number }>(
    `/integrations/webhooks/${id}/test`,
    { method: "POST" },
  );
}

export function deleteWebhook(id: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/integrations/webhooks/${id}`, {
    method: "DELETE",
  });
}

// ─── third-party ──────────────────────────────────────────────────────

export function listThirdParty(): Promise<{ items: ThirdPartyIntegration[] }> {
  return request<{ items: ThirdPartyIntegration[] }>(
    "/integrations/third-party",
  );
}

export function connectThirdParty(
  slug: string,
  config: Record<string, unknown>,
  display_label?: string,
): Promise<ThirdPartyIntegration> {
  return request<ThirdPartyIntegration>("/integrations/third-party", {
    method: "POST",
    body: JSON.stringify({ provider_slug: slug, config, display_label }),
  });
}

export function disconnectThirdParty(id: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/integrations/third-party/${id}`, {
    method: "DELETE",
  });
}

// ─── logs ─────────────────────────────────────────────────────────────

export function listLogs(params: {
  limit?: number;
  source?: IntegrationLog["source"];
} = {}): Promise<{ items: IntegrationLog[] }> {
  const qs = new URLSearchParams();
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.source) qs.set("source", params.source);
  return request<{ items: IntegrationLog[] }>(
    `/integrations/logs${qs.toString() ? "?" + qs : ""}`,
  );
}

// ─── events emit (for testing) ────────────────────────────────────────

export function emitEvent(
  event_type: string,
  payload: Record<string, unknown>,
): Promise<{ ok: boolean; dispatched: number }> {
  return request<{ ok: boolean; dispatched: number }>(
    "/integrations/events/emit",
    {
      method: "POST",
      body: JSON.stringify({ event_type, payload }),
    },
  );
}

export { IntegrationsApiError };
