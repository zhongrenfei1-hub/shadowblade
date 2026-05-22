import { headers } from "next/headers";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { IntegrationsEditor } from "@/components/workspace/integrations-editor";
import {
  getOverview,
  listApiKeys,
  listProviders,
  listThirdParty,
  listWebhooks,
} from "@/lib/api/integrations";

async function loadIntegrations() {
  headers();
  try {
    const [overview, apiKeys, webhooks, thirdParty, providers] =
      await Promise.all([
        getOverview(),
        listApiKeys(),
        listWebhooks(),
        listThirdParty(),
        listProviders(),
      ]);
    return {
      overview,
      apiKeys: apiKeys.items,
      webhooks: webhooks.items,
      thirdParty: thirdParty.items,
      providers: providers.items,
      error: null,
    };
  } catch (err) {
    return {
      overview: null,
      apiKeys: [],
      webhooks: [],
      thirdParty: [],
      providers: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export default async function IntegrationsPage() {
  const {
    overview,
    apiKeys,
    webhooks,
    thirdParty,
    providers,
    error,
  } = await loadIntegrations();

  if (error || !overview) {
    return (
      <section className="grid gap-4">
        <h1 className="font-display text-2xl font-semibold">集成</h1>
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">无法加载集成</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-xs text-destructive">{error}</p>
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          集成
        </span>
        <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
          API Keys · Webhooks · 第三方
        </h1>
        <p className="max-w-prose text-sm text-muted-foreground">
          配置外部访问 ShadowBlade 的密钥、渲染事件回调、Slack/Discord/Notion 通知。
          所有操作走 /api/v1/integrations/*。
        </p>
      </section>

      <IntegrationsEditor
        overview={overview}
        initialApiKeys={apiKeys}
        initialWebhooks={webhooks}
        initialThirdParty={thirdParty}
        providers={providers}
      />
    </>
  );
}
