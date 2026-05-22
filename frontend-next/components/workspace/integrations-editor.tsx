"use client";

import { useState } from "react";
import {
  Loader2,
  Trash2,
  Plus,
  Activity,
  KeyRound,
  Webhook as WebhookIcon,
  Plug,
  Copy,
} from "lucide-react";
import {
  type ApiKey,
  type ApiKeyCreated,
  type IntegrationsOverview,
  type Provider,
  type ThirdPartyIntegration,
  type Webhook,
  connectThirdParty,
  createApiKey,
  createWebhook,
  deleteWebhook,
  disconnectThirdParty,
  listApiKeys,
  listThirdParty,
  listWebhooks,
  revokeApiKey,
  testWebhook,
} from "@/lib/api/integrations";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface Props {
  overview: IntegrationsOverview;
  initialApiKeys: ApiKey[];
  initialWebhooks: Webhook[];
  initialThirdParty: ThirdPartyIntegration[];
  providers: Provider[];
}

type Tab = "keys" | "webhooks" | "third";

export function IntegrationsEditor({
  overview,
  initialApiKeys,
  initialWebhooks,
  initialThirdParty,
  providers,
}: Props) {
  const [tab, setTab] = useState<Tab>("keys");
  const [apiKeys, setApiKeys] = useState(initialApiKeys);
  const [webhooks, setWebhooks] = useState(initialWebhooks);
  const [thirdParty, setThirdParty] = useState(initialThirdParty);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<ApiKeyCreated | null>(null);
  const [webhookTestResult, setWebhookTestResult] = useState<
    Record<number, string>
  >({});

  // API key form
  const [keyName, setKeyName] = useState("");
  // Webhook form
  const [hookUrl, setHookUrl] = useState("");
  const [hookEvents, setHookEvents] = useState("render.completed,render.failed");
  // Third-party form
  const [selectedProvider, setSelectedProvider] = useState(
    providers[0]?.slug ?? "",
  );
  const [providerConfigKey, setProviderConfigKey] = useState("webhook_url");
  const [providerConfigValue, setProviderConfigValue] = useState("");

  async function handleCreateKey(e: React.FormEvent) {
    e.preventDefault();
    if (!keyName.trim()) return;
    setBusy("key-create");
    setError(null);
    try {
      const created = await createApiKey(keyName.trim(), ["read", "write"]);
      setRevealed(created);
      setKeyName("");
      const next = await listApiKeys();
      setApiKeys(next.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleRevokeKey(id: number) {
    if (!confirm("确认撤销该 API key？")) return;
    setBusy(`key-${id}`);
    try {
      await revokeApiKey(id);
      setApiKeys((ks) => ks.filter((k) => k.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleCreateWebhook(e: React.FormEvent) {
    e.preventDefault();
    if (!hookUrl.startsWith("http")) {
      setError("URL 必须 http(s)://");
      return;
    }
    setBusy("hook-create");
    setError(null);
    try {
      const events = hookEvents
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const w = await createWebhook(hookUrl.trim(), events);
      setWebhooks((ws) => [w, ...ws]);
      setHookUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleTestWebhook(id: number) {
    setBusy(`hook-test-${id}`);
    setWebhookTestResult((r) => ({ ...r, [id]: "" }));
    try {
      const r = await testWebhook(id);
      setWebhookTestResult((s) => ({
        ...s,
        [id]: r.ok
          ? `✓ ${r.status_code} · ${r.took_ms}ms`
          : `✗ ${r.status_code}`,
      }));
    } catch (err) {
      setWebhookTestResult((s) => ({
        ...s,
        [id]: `✗ ${err instanceof Error ? err.message : String(err)}`,
      }));
    } finally {
      setBusy(null);
    }
  }

  async function handleDeleteWebhook(id: number) {
    if (!confirm("确认删除该 webhook？")) return;
    setBusy(`hook-${id}`);
    try {
      await deleteWebhook(id);
      setWebhooks((ws) => ws.filter((w) => w.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleConnectThird(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProvider || !providerConfigValue.trim()) return;
    setBusy("third-connect");
    setError(null);
    try {
      const conn = await connectThirdParty(selectedProvider, {
        [providerConfigKey]: providerConfigValue.trim(),
      });
      setThirdParty((ts) => [conn, ...ts]);
      setProviderConfigValue("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleDisconnectThird(id: number) {
    if (!confirm("确认断开该第三方集成？")) return;
    setBusy(`third-${id}`);
    try {
      await disconnectThirdParty(id);
      setThirdParty((ts) => ts.filter((t) => t.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>集成概览</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric
              icon={<KeyRound className="h-4 w-4" />}
              label="API Keys"
              value={`${overview.api_keys_active}/${overview.api_keys_total}`}
            />
            <Metric
              icon={<WebhookIcon className="h-4 w-4" />}
              label="Webhooks"
              value={`${overview.webhooks_active}/${overview.webhooks_total}`}
            />
            <Metric
              icon={<Plug className="h-4 w-4" />}
              label="第三方"
              value={`${overview.third_party_active}/${overview.third_party_total}`}
            />
            <Metric
              icon={<Activity className="h-4 w-4" />}
              label="最近事件"
              value={String(overview.recent_events.length)}
            />
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="p-4 font-mono text-xs text-destructive">
            {error}
          </CardContent>
        </Card>
      )}

      {revealed && (
        <Card className="border-accent-500/40 bg-accent-500/10">
          <CardHeader>
            <CardTitle>🔑 新 API key — 仅本次显示，请立即复制</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all rounded-md border border-border bg-background p-3 font-mono text-xs">
                {revealed.plaintext}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() => {
                  navigator.clipboard.writeText(revealed.plaintext);
                }}
                aria-label="复制"
              >
                <Copy className="h-4 w-4" aria-hidden />
              </Button>
            </div>
            <Button
              variant="ghost"
              className="mt-3"
              onClick={() => setRevealed(null)}
            >
              我已保存，关闭
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-2">
        {(
          [
            ["keys", "API Keys"],
            ["webhooks", "Webhooks"],
            ["third", "第三方"],
          ] as [Tab, string][]
        ).map(([k, label]) => (
          <Button
            key={k}
            variant={tab === k ? "default" : "outline"}
            onClick={() => setTab(k)}
          >
            {label}
          </Button>
        ))}
      </div>

      {tab === "keys" && (
        <Card>
          <CardHeader>
            <CardTitle>API Keys（{apiKeys.length}）</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              {apiKeys.map((k) => (
                <div
                  key={k.id}
                  className="grid grid-cols-[1fr_120px_44px] items-center gap-3 rounded-md border border-border bg-card/40 p-3"
                >
                  <div className="grid leading-tight">
                    <b className="text-sm">{k.name}</b>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {k.masked} · scopes [{k.scopes.join(", ")}]
                    </span>
                  </div>
                  <Badge variant={k.is_active ? "done" : "failed"}>
                    {k.is_active ? "启用" : "撤销"}
                  </Badge>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleRevokeKey(k.id)}
                    disabled={busy === `key-${k.id}`}
                    aria-label="撤销"
                  >
                    {busy === `key-${k.id}` ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Trash2 className="h-4 w-4" aria-hidden />
                    )}
                  </Button>
                </div>
              ))}
              {apiKeys.length === 0 && (
                <p className="rounded-md border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
                  还没有任何 API key。
                </p>
              )}
            </div>
            <form
              onSubmit={handleCreateKey}
              className="mt-4 grid gap-2 sm:grid-cols-[1fr_140px]"
            >
              <Input
                placeholder="新 key 的描述名，如 'CI 部署用'"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                required
              />
              <Button type="submit" disabled={busy === "key-create"}>
                {busy === "key-create" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <Plus className="h-4 w-4" aria-hidden />
                )}
                <span>创建</span>
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {tab === "webhooks" && (
        <Card>
          <CardHeader>
            <CardTitle>Webhooks（{webhooks.length}）</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              {webhooks.map((w) => (
                <div
                  key={w.id}
                  className="grid gap-2 rounded-md border border-border bg-card/40 p-3"
                >
                  <div className="grid grid-cols-[1fr_120px_44px] items-center gap-3">
                    <div className="grid leading-tight">
                      <b className="break-all text-sm">{w.url}</b>
                      <span className="text-[11px] text-muted-foreground">
                        events: {w.events.join(", ")}
                      </span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestWebhook(w.id)}
                      disabled={busy === `hook-test-${w.id}`}
                    >
                      {busy === `hook-test-${w.id}` ? (
                        <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                      ) : null}
                      测试
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => handleDeleteWebhook(w.id)}
                      disabled={busy === `hook-${w.id}`}
                      aria-label="删除"
                    >
                      {busy === `hook-${w.id}` ? (
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                      ) : (
                        <Trash2 className="h-4 w-4" aria-hidden />
                      )}
                    </Button>
                  </div>
                  {webhookTestResult[w.id] && (
                    <p className="font-mono text-[11px] text-accent-300">
                      {webhookTestResult[w.id]}
                    </p>
                  )}
                </div>
              ))}
              {webhooks.length === 0 && (
                <p className="rounded-md border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
                  还没有任何 webhook。
                </p>
              )}
            </div>
            <form
              onSubmit={handleCreateWebhook}
              className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_120px]"
            >
              <div className="grid gap-1">
                <Label htmlFor="hook-url" className="text-xs">URL</Label>
                <Input
                  id="hook-url"
                  placeholder="https://httpbin.org/post"
                  value={hookUrl}
                  onChange={(e) => setHookUrl(e.target.value)}
                  required
                />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="hook-events" className="text-xs">
                  事件（逗号分隔）
                </Label>
                <Input
                  id="hook-events"
                  value={hookEvents}
                  onChange={(e) => setHookEvents(e.target.value)}
                />
              </div>
              <div className="grid items-end">
                <Button type="submit" disabled={busy === "hook-create"}>
                  {busy === "hook-create" ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    <Plus className="h-4 w-4" aria-hidden />
                  )}
                  <span>创建</span>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {tab === "third" && (
        <Card>
          <CardHeader>
            <CardTitle>第三方集成（{thirdParty.length}）</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              {thirdParty.map((t) => (
                <div
                  key={t.id}
                  className="grid grid-cols-[1fr_120px_44px] items-center gap-3 rounded-md border border-border bg-card/40 p-3"
                >
                  <div className="grid leading-tight">
                    <b className="text-sm">{t.display_label}</b>
                    <span className="text-[11px] text-muted-foreground">
                      {t.provider_slug} · {t.config_summary ?? "已连接"}
                    </span>
                  </div>
                  <Badge variant={t.is_active ? "done" : "failed"}>
                    {t.is_active ? "已连接" : "已断开"}
                  </Badge>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleDisconnectThird(t.id)}
                    disabled={busy === `third-${t.id}`}
                    aria-label="断开"
                  >
                    {busy === `third-${t.id}` ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Trash2 className="h-4 w-4" aria-hidden />
                    )}
                  </Button>
                </div>
              ))}
            </div>
            <form
              onSubmit={handleConnectThird}
              className="mt-4 grid gap-3 sm:grid-cols-[180px_180px_1fr_120px]"
            >
              <div className="grid gap-1">
                <Label htmlFor="provider" className="text-xs">Provider</Label>
                <select
                  id="provider"
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="h-9 rounded-md border border-border bg-background px-2 text-sm"
                >
                  {providers.map((p) => (
                    <option key={p.slug} value={p.slug}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid gap-1">
                <Label htmlFor="cfg-key" className="text-xs">配置 key</Label>
                <Input
                  id="cfg-key"
                  value={providerConfigKey}
                  onChange={(e) => setProviderConfigKey(e.target.value)}
                />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="cfg-val" className="text-xs">配置 value</Label>
                <Input
                  id="cfg-val"
                  value={providerConfigValue}
                  onChange={(e) => setProviderConfigValue(e.target.value)}
                  placeholder={
                    providers.find((p) => p.slug === selectedProvider)
                      ?.config_hint ?? ""
                  }
                  required
                />
              </div>
              <div className="grid items-end">
                <Button type="submit" disabled={busy === "third-connect"}>
                  {busy === "third-connect" ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  ) : (
                    <Plus className="h-4 w-4" aria-hidden />
                  )}
                  <span>连接</span>
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="grid gap-1 rounded-md border border-border bg-card/40 p-3">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="font-display text-xl font-semibold">{value}</div>
    </div>
  );
}
