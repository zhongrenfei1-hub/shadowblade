import Link from "next/link";
import { Video, Clock, CheckCircle2, DollarSign, Play, RefreshCw, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiTile } from "@/components/workspace/kpi-tile";
import { PipelineStage } from "@/components/workspace/pipeline-stage";
import { ProjectCard } from "@/components/workspace/project-card";
import { StatusBadge } from "@/components/workspace/status-badge";

const STAGES = [
  { idx: 1, title: "脚本", log: "6 个场景 · 142 字 · 品牌语态评分 0.94", meta: "8.4 秒", state: "succeeded" as const },
  { idx: 2, title: "分镜", log: "6/6 分镜已渲染 · 编辑风格", meta: "12.1 秒", state: "succeeded" as const },
  { idx: 3, title: "配音", log: "alloy-en-female · 4 个版本 · -14 LUFS", meta: "18.6 秒", state: "succeeded" as const },
  { idx: 4, title: "空镜素材匹配", log: "匹配 18 段素材 · 已开启 CC 协议过滤", meta: "41.0 秒", state: "succeeded" as const },
  { idx: 5, title: "合成", log: "62% · 等待叠加层 #3 · 1280×2272", meta: "预计 0:64", state: "running" as const },
  { idx: 6, title: "渲染为 MP4", log: "排在 2 个加急任务之后 · H.264 high · 60 fps", meta: "排队中" },
];

const APPROVALS = [
  { initials: "SE", title: "入职培训 · 销售工程师训练营", log: "Marcus Lee · 2 条评论 · 96 秒", action: "审核", primary: true },
  { initials: "CP", title: "AI Copilot · 产品演示", log: "Priya Rao · 第 3 版 · 60 秒", action: "打开" },
  { initials: "SR", title: "C 轮预告 · TikTok", log: "Diego Alvarez · 待发布", action: "批准", primary: true },
];

export default async function DashboardPage() {
  const { items: projects } = await api.projects();

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">工作台概览</span>
        <div className="flex items-end gap-6">
          <div>
            <h1 className="font-display text-[34px] font-semibold tracking-tight">Ava，欢迎回来。</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              本周已交付 6 条成片，当前 2 条在跑。流水线按周二产品发布日程推进中。
            </p>
          </div>
          <div className="ml-auto flex gap-3">
            <Button variant="outline">
              <RefreshCw className="h-3.5 w-3.5" />
              刷新
            </Button>
            <Button asChild>
              <Link href="/create">
                <Sparkles className="h-4 w-4" />
                一键生成视频
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-4 gap-4" aria-label="关键指标">
        <KpiTile icon={Video} label="本月渲染次数" value="387" suffix="/ 1,000" delta="12.4% 较上月" />
        <KpiTile icon={Clock} label="首版成片耗时" value="4.8" suffix="分钟" delta="提速 31%" />
        <KpiTile icon={CheckCircle2} label="一次审核通过率" value="92" suffix="%" delta="6 个百分点" />
        <KpiTile icon={DollarSign} label="较外包代理节省" value="$168k" suffix="/季度" delta="21%" />
      </section>

      <section className="grid grid-cols-[2fr_1fr] gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center gap-3">
            <div className="flex-1">
              <CardTitle>进行中 · 流程运行</CardTitle>
              <p className="mt-0.5 text-sm text-muted-foreground">春季产品发布 — 智能腕环 · 28 秒 · 9:16</p>
            </div>
            <StatusBadge status="rendering" />
            <Button variant="outline" size="sm" asChild>
              <Link href="/projects/101">在编辑器中打开</Link>
            </Button>
          </CardHeader>
          <CardContent className="grid gap-2.5">
            {STAGES.map((s) => (
              <PipelineStage key={s.idx} index={s.idx} title={s.title} log={s.log} meta={s.meta} state={s.state} />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>等你审批</CardTitle>
            <Button variant="outline" size="sm">查看全部</Button>
          </CardHeader>
          <CardContent className="grid gap-3">
            {APPROVALS.map((a) => (
              <div key={a.title} className="grid grid-cols-[28px_1fr_auto] items-center gap-3 rounded-md border border-border bg-card/40 px-4 py-3">
                <span className="grid h-6 w-6 place-items-center rounded-md bg-accent-500/15 font-mono text-[11px] text-accent-300">
                  {a.initials}
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold">{a.title}</div>
                  <div className="truncate font-mono text-[11px] text-muted-foreground">{a.log}</div>
                </div>
                <Button size="sm" variant={a.primary ? "default" : "outline"}>{a.action}</Button>
              </div>
            ))}
            <div className="h-px bg-border" />
            <div className="grid grid-cols-[28px_1fr_auto] items-center gap-3 rounded-md border border-border bg-card/40 px-4 py-3">
              <span className="grid h-6 w-6 place-items-center rounded-md bg-amber-500/15 text-[11px] text-amber-300">!</span>
              <div className="min-w-0">
                <div className="text-sm font-semibold">品牌规范偏移</div>
                <div className="truncate text-xs text-muted-foreground">2 条成片使用了 #20D2B5——应为 #22D3B7。</div>
              </div>
              <Button size="sm" variant="outline">解决</Button>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4">
        <div className="flex items-end gap-6">
          <div>
            <h2 className="font-display text-xl font-semibold">最近项目</h2>
            <p className="mt-1 text-sm text-muted-foreground">共 38 个 · 按最近编辑排序</p>
          </div>
          <div className="ml-auto flex gap-2">
            {["全部", "营销", "培训", "演示", "社交"].map((t, i) => (
              <Button key={t} size="sm" variant={i === 0 ? "default" : "outline"}>{t}</Button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4">
          {projects.map((p) => <ProjectCard key={p.id} project={p} />)}
        </div>
      </section>
    </>
  );
}
