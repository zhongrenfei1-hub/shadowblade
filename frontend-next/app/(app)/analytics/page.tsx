import { headers } from "next/headers";
import {
  Video,
  Activity,
  TrendingUp,
  HardDrive,
  CheckCircle2,
  Clock,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  getOverview,
  getTrends,
  type AnalyticsKpi,
  type AnalyticsOverview,
  type AnalyticsTrends,
} from "@/lib/api/analytics";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  videos_total: Video,
  renders_total: Activity,
  success_rate: CheckCircle2,
  avg_runtime_seconds: Clock,
  total_runtime_seconds: TrendingUp,
  storage_bytes: HardDrive,
};

function formatKpi(kpi: AnalyticsKpi): { value: string; suffix?: string } {
  switch (kpi.unit) {
    case "ratio":
      return { value: `${Math.round(kpi.value * 100)}`, suffix: "%" };
    case "seconds":
      return { value: kpi.value.toFixed(1), suffix: "秒" };
    case "bytes": {
      const mb = kpi.value / 1024 / 1024;
      if (mb < 1024) return { value: mb.toFixed(1), suffix: "MB" };
      return { value: (mb / 1024).toFixed(2), suffix: "GB" };
    }
    case "count":
      return { value: kpi.value.toLocaleString("zh-CN") };
    default:
      return { value: String(kpi.value), suffix: kpi.unit };
  }
}

async function loadAnalytics(): Promise<{
  overview: AnalyticsOverview | null;
  trends: AnalyticsTrends | null;
  error: string | null;
}> {
  headers();
  try {
    const [overview, trends] = await Promise.all([
      getOverview("30d"),
      getTrends("30d").catch(() => null),
    ]);
    return { overview, trends, error: null };
  } catch (err) {
    return {
      overview: null,
      trends: null,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export default async function AnalyticsPage() {
  const { overview, trends, error } = await loadAnalytics();

  if (error || !overview) {
    return (
      <section className="grid gap-4">
        <h1 className="font-display text-2xl font-semibold">数据分析</h1>
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">
              无法加载 /api/v1/analytics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-xs text-destructive">{error}</p>
          </CardContent>
        </Card>
      </section>
    );
  }

  const maxRender = trends
    ? Math.max(1, ...trends.points.map((p) => p.renders))
    : 1;

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          数据分析 · live · 最近 {overview.period}
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              workspace #{overview.workspace_id}
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              {new Date(overview.from).toLocaleDateString("zh-CN")} →{" "}
              {new Date(overview.to).toLocaleDateString("zh-CN")} · 数据{" "}
              {overview.cached ? "缓存" : "实时"}
            </p>
          </div>
          <Button variant="outline" asChild>
            <a href="/analytics">
              <RefreshCw className="h-3.5 w-3.5" aria-hidden />
              <span>刷新</span>
            </a>
          </Button>
        </div>
      </section>

      <section
        className="grid grid-cols-2 gap-4 lg:grid-cols-3"
        aria-label="关键指标"
      >
        {overview.kpis.map((k) => {
          const Icon = ICONS[k.key] ?? Activity;
          const f = formatKpi(k);
          return (
            <Card key={k.key}>
              <CardContent className="grid gap-2 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    {k.label}
                  </span>
                  <Icon className="h-4 w-4 text-accent-300" />
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="font-display text-3xl font-semibold">
                    {f.value}
                  </span>
                  {f.suffix && (
                    <span className="text-xs text-muted-foreground">
                      {f.suffix}
                    </span>
                  )}
                </div>
                <span className="font-mono text-[10px] text-muted-foreground">
                  {k.key}
                </span>
              </CardContent>
            </Card>
          );
        })}
      </section>

      {trends && trends.points.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>渲染趋势 · {trends.granularity}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-40 items-end gap-1">
              {trends.points.map((p) => {
                const h = (p.renders / maxRender) * 100;
                return (
                  <div
                    key={p.bucket}
                    className="grid flex-1 gap-1 text-center"
                  >
                    <div className="grid items-end" style={{ height: 128 }}>
                      <div
                        className="w-full rounded-t-sm bg-accent-500/70 transition-all"
                        style={{ height: `${h}%`, minHeight: 2 }}
                        title={`${p.bucket}: ${p.renders} 渲染 / ${p.success} 成功 / ${p.failures} 失败`}
                      />
                    </div>
                    <span className="font-mono text-[9px] text-muted-foreground">
                      {p.bucket.slice(5)}
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>视频用途分布</CardTitle>
          </CardHeader>
          <CardContent>
            <Distribution items={overview.distribution} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>渲染状态分布</CardTitle>
          </CardHeader>
          <CardContent>
            <Distribution items={overview.status_distribution} />
          </CardContent>
        </Card>
      </section>

      {Object.keys(overview.totals).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>汇总指标</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
              {Object.entries(overview.totals).map(([k, v]) => (
                <div
                  key={k}
                  className="grid gap-1 rounded-md border border-border bg-card/40 p-3"
                >
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {k}
                  </span>
                  <span className="font-display text-lg">
                    {typeof v === "number"
                      ? v.toLocaleString("zh-CN")
                      : String(v)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}

function Distribution({
  items,
}: {
  items: { label: string; value: number }[];
}) {
  const total = items.reduce((sum, i) => sum + i.value, 0) || 1;
  return (
    <div className="grid gap-2">
      {items.map((it) => {
        const pct = (it.value / total) * 100;
        return (
          <div key={it.label} className="grid gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono">{it.label}</span>
              <span className="text-muted-foreground">
                {it.value} · {Math.round(pct)}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-border">
              <div
                className="h-full bg-accent-500"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
      {items.length === 0 && (
        <p className="text-center text-sm text-muted-foreground">
          暂无数据
        </p>
      )}
    </div>
  );
}
