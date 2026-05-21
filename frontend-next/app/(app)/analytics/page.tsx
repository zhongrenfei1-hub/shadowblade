import { Video, Clock, CheckCircle2, DollarSign, Download, RefreshCw, Calendar, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { KpiTile } from "@/components/workspace/kpi-tile";

const ICONS = [Video, Clock, CheckCircle2, DollarSign];

const LEADERBOARD = [
  { name: "Ava Chen", role: "工作空间管理员", cuts: 128, delta: "+18", approval: "95%", avg: "4.2 分钟" },
  { name: "Marcus Lee", role: "制作人", cuts: 91, delta: "+9", approval: "93%", avg: "4.6 分钟" },
  { name: "Priya Rao", role: "品牌负责人", cuts: 82, delta: "+14", approval: "96%", avg: "5.1 分钟" },
  { name: "Diego Alvarez", role: "审核员", cuts: 42, delta: "+4", approval: "90%", avg: "5.4 分钟" },
];

const RATIO = [
  { label: "9:16 竖屏", pct: 62 },
  { label: "16:9 横屏", pct: 28 },
  { label: "1:1 方形", pct: 10 },
];

const DRIFT = [
  { kind: "warn", title: "色彩偏移 · 2 条成片", desc: "用了 #20D2B5，应为 #22D3B7 · 可一键自动修正", action: "解决" },
  { kind: "stop", title: "配音错配 · 1 条成片", desc: "Acme · 核心版要求灵韵女声，实际用了炽炎男声", action: "重新渲染" },
  { kind: "ok", title: "最近 100 条全部合规", desc: "无片尾缺失 · 无字体回退 · 无版权风险", action: undefined },
];

const KIND_CLASS: Record<string, string> = {
  warn: "border-amber-500/30 bg-amber-500/[0.05] text-amber-300",
  stop: "border-rose-500/30 bg-rose-500/[0.05] text-rose-300",
  ok: "border-accent-500/30 bg-accent-500/[0.05] text-accent-300",
};

function formatKpi(label: string, value: number, unit: string) {
  if (unit === "ratio") return { value: `${Math.round(value * 100)}`, suffix: "%" };
  if (unit === "minutes") return { value: value.toFixed(1), suffix: "分钟" };
  if (unit === "usd") return { value: `$${(value / 1000).toFixed(0)}k`, suffix: "/季度" };
  return { value: value.toLocaleString("zh-CN"), suffix: undefined };
}

function formatDelta(delta: number) {
  const sign = delta >= 0 ? "▲" : "▼";
  return `${sign} ${Math.abs(delta * 100).toFixed(1)}%`;
}

export default async function AnalyticsPage() {
  const a = await api.analytics();
  const maxRendered = Math.max(...a.timeseries.map((d) => d.rendered));

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">数据分析 · 最近 7 天</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              产量在涨，首版耗时在降。
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              本周交付 387 条成片，一次审核通过 92%。营销组贡献产量最高；产品演示提速最猛。
            </p>
          </div>
          <div className="flex flex-wrap gap-2 md:gap-3">
            <Button variant="outline" aria-label="切换时间窗口">
              <Calendar className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">最近 7 天</span>
            </Button>
            <Button variant="outline">
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">导出 CSV</span>
            </Button>
            <Button>
              <RefreshCw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">刷新</span>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4" aria-label="关键指标">
        {a.kpis.map((kpi, i) => {
          const f = formatKpi(kpi.label, kpi.value, kpi.unit);
          return (
            <KpiTile
              key={kpi.label}
              icon={ICONS[i % ICONS.length]}
              label={kpi.label}
              value={f.value}
              suffix={f.suffix}
              delta={formatDelta(kpi.delta)}
              positive={kpi.delta > 0 || (kpi.unit === "minutes" && kpi.delta < 0)}
            />
          );
        })}
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-end gap-3">
            <div className="flex-1">
              <CardTitle>渲染 · 最近 7 天</CardTitle>
              <p className="mt-0.5 text-sm text-muted-foreground">绿色 = 一次过审，琥珀 = 被驳回</p>
            </div>
            <Badge variant="done">通过 358</Badge>
            <Badge variant="queued">驳回 29</Badge>
          </CardHeader>
          <CardContent>
            <div className="flex h-[240px] items-end gap-3 px-2">
              {a.timeseries.map((d) => {
                const approvedH = (d.approved / maxRendered) * 100;
                const rejectedH = (d.rejected / maxRendered) * 100;
                return (
                  <div key={d.day} className="flex flex-1 flex-col items-center gap-1.5">
                    <div className="flex w-full flex-1 flex-col-reverse gap-0.5">
                      <div className="rounded-t bg-accent-500/85" style={{ height: `${approvedH}%` }} aria-label={`${d.day} 通过 ${d.approved}`} />
                      <div className="rounded-t bg-amber-400/85" style={{ height: `${rejectedH}%` }} aria-label={`${d.day} 驳回 ${d.rejected}`} />
                    </div>
                    <span className="text-[11px] text-muted-foreground">{d.day}</span>
                    <span className="font-mono text-[10px] text-foreground/80">{d.rendered}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>用途分布</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {a.distribution.map((d) => (
              <div key={d.label} className="grid grid-cols-[100px_1fr_42px] items-center gap-3 text-sm">
                <span className="truncate text-muted-foreground">{d.label}</span>
                <div className="h-2 overflow-hidden rounded-full bg-white/[0.05]">
                  <div className="h-full rounded-full bg-gradient-to-r from-accent-500 to-sky-400" style={{ width: `${d.value}%` }} />
                </div>
                <span className="text-right font-mono text-[12px] text-muted-foreground num">{d.value}%</span>
              </div>
            ))}
            <div className="h-px bg-border" />
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">最受欢迎画幅</div>
            {RATIO.map((r) => (
              <div key={r.label} className="grid grid-cols-[100px_1fr_42px] items-center gap-3 text-sm">
                <span className="truncate text-muted-foreground">{r.label}</span>
                <div className="h-2 overflow-hidden rounded-full bg-white/[0.05]">
                  <div className="h-full rounded-full bg-gradient-to-r from-accent-500 to-sky-400" style={{ width: `${r.pct}%` }} />
                </div>
                <span className="text-right font-mono text-[12px] text-muted-foreground num">{r.pct}%</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>制作人排行榜</CardTitle>
            <Button size="sm" variant="outline">最近 30 天</Button>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b border-border text-[10px] uppercase tracking-wider text-muted-foreground">
                  <th className="px-3 py-2 text-left font-semibold">制作人</th>
                  <th className="px-3 py-2 text-right font-semibold">条数</th>
                  <th className="px-3 py-2 text-right font-semibold">通过率</th>
                  <th className="px-3 py-2 text-right font-semibold">平均耗时</th>
                </tr>
              </thead>
              <tbody>
                {LEADERBOARD.map((p) => (
                  <tr key={p.name} className="border-b border-border last:border-0 hover:bg-white/[0.025]">
                    <td className="px-3 py-3">
                      <b className="block font-semibold">{p.name}</b>
                      <span className="text-[11px] text-muted-foreground">{p.role}</span>
                    </td>
                    <td className="px-3 py-3 text-right font-mono num">
                      {p.cuts}
                      <span className="ml-1.5 font-semibold text-accent-300">{p.delta}</span>
                    </td>
                    <td className="px-3 py-3 text-right font-mono num">{p.approval}</td>
                    <td className="px-3 py-3 text-right font-mono num">{p.avg}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>品牌偏移告警</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            {DRIFT.map((d) => (
              <div key={d.title} className={`grid grid-cols-[28px_1fr_auto] items-start gap-3 rounded-md border px-3 py-3 ${KIND_CLASS[d.kind]}`}>
                {d.kind === "ok" ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5" aria-hidden />
                ) : (
                  <AlertTriangle className="mt-0.5 h-5 w-5" aria-hidden />
                )}
                <div className="min-w-0 text-foreground">
                  <div className="text-sm font-semibold">{d.title}</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">{d.desc}</div>
                </div>
                {d.action && <Button size="sm" variant="outline">{d.action}</Button>}
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </>
  );
}
