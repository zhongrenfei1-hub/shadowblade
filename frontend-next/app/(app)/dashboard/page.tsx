import Link from "next/link";
import {
  Sparkles,
  RefreshCw,
  Video,
  Calendar,
  Activity,
  FolderKanban,
  PlayCircle,
} from "lucide-react";
import { headers } from "next/headers";
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
  listActiveTasks,
  listRecentProjects,
  type ActiveTask,
  type RecentProject,
  type WorkbenchKpi,
  type WorkbenchOverview,
} from "@/lib/api/workbench";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  renders_today: Video,
  renders_this_week: Calendar,
  in_progress: Activity,
  total_projects: FolderKanban,
};

async function loadDashboard(): Promise<{
  overview: WorkbenchOverview | null;
  recent: RecentProject[];
  active: ActiveTask[];
  error: string | null;
}> {
  headers();
  try {
    const [overview, recentRes, activeRes] = await Promise.all([
      getOverview(),
      listRecentProjects(),
      listActiveTasks(),
    ]);
    return {
      overview,
      recent: recentRes.items,
      active: activeRes.items,
      error: null,
    };
  } catch (err) {
    return {
      overview: null,
      recent: [],
      active: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export default async function DashboardPage() {
  const { overview, recent, active, error } = await loadDashboard();

  if (error || !overview) {
    return (
      <section className="grid gap-4">
        <h1 className="font-display text-2xl font-semibold">工作台</h1>
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">无法加载工作台</CardTitle>
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
          工作台概览 · 实时
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              workspace #{overview.workspace_id} 全景
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              数据来自 /api/v1/workbench/overview · 生成于{" "}
              {new Date(overview.generated_at).toLocaleString("zh-CN")}
            </p>
          </div>
          <div className="flex gap-2 md:gap-3">
            <Button variant="outline" asChild>
              <Link href="/dashboard">
                <RefreshCw className="h-3.5 w-3.5" aria-hidden />
                <span className="hidden sm:inline">刷新</span>
              </Link>
            </Button>
            <Button asChild>
              <Link href="/studio">
                <Sparkles className="h-4 w-4" aria-hidden />
                <span className="hidden sm:inline">新建视频</span>
                <span className="sm:hidden">新建</span>
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <section
        className="grid grid-cols-2 gap-4 lg:grid-cols-4"
        aria-label="关键指标 · 实时"
      >
        {overview.kpis.map((k) => (
          <KpiCard key={k.key} kpi={k} />
        ))}
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>进行中 · {active.length} 个任务</CardTitle>
            <Badge variant="rendering">live · render queue</Badge>
          </CardHeader>
          <CardContent>
            {active.length === 0 ? (
              <p className="rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                当前没有进行中的任务。
              </p>
            ) : (
              <div className="grid gap-2">
                {active.map((t) => (
                  <ActiveTaskRow key={t.task_id} task={t} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>当前品牌套件</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.brand_kit ? (
              <div className="grid gap-3">
                <div className="flex items-center gap-3">
                  <span
                    aria-hidden
                    className="h-12 w-12 rounded-md border border-border"
                    style={{
                      background: `linear-gradient(135deg,${overview.brand_kit.primary_color},${overview.brand_kit.accent_color})`,
                    }}
                  />
                  <div className="leading-tight">
                    <b className="text-sm">{overview.brand_kit.name}</b>
                    <span className="block font-mono text-[11px] text-muted-foreground">
                      kit #{overview.brand_kit.id} · scope{" "}
                      {overview.brand_kit.scope}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[10px]">
                  <Swatch label="主" color={overview.brand_kit.primary_color} />
                  <Swatch
                    label="强"
                    color={overview.brand_kit.accent_color}
                  />
                  <Swatch
                    label="辅"
                    color={overview.brand_kit.secondary_color}
                  />
                </div>
                <p className="text-[11px] text-muted-foreground">
                  字体 {overview.brand_kit.font_heading} ·{" "}
                  {overview.brand_kit.voice}
                </p>
                <Button asChild variant="outline" size="sm">
                  <Link href="/brand">编辑套件</Link>
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">未配置品牌套件。</p>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-3">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold">最近项目</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              来自 /workbench/recent-projects · {recent.length} 个
            </p>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/projects">全部项目</Link>
          </Button>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {recent.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      </section>

      {overview.featured_templates.length > 0 && (
        <section className="grid gap-3">
          <div className="flex items-end justify-between">
            <h2 className="font-display text-xl font-semibold">推荐模板</h2>
            <Button variant="outline" size="sm" asChild>
              <Link href="/templates">所有模板</Link>
            </Button>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {overview.featured_templates.slice(0, 4).map((t) => (
              <Card key={t.name}>
                <CardHeader>
                  <CardTitle className="text-sm">{t.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-[11px] text-muted-foreground">
                    {t.description}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {t.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="draft">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function KpiCard({ kpi }: { kpi: WorkbenchKpi }) {
  const Icon = ICONS[kpi.key] ?? Activity;
  return (
    <Card>
      <CardContent className="grid gap-2 p-5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {kpi.label}
          </span>
          <Icon className="h-4 w-4 text-accent-300" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="font-display text-3xl font-semibold">
            {kpi.value}
          </span>
          <span className="text-xs text-muted-foreground">{kpi.unit}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function ActiveTaskRow({ task }: { task: ActiveTask }) {
  const progressPct = Math.round(task.progress * 100);
  return (
    <div className="grid gap-2 rounded-md border border-border bg-card/40 p-3">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <b className="block truncate text-sm">{task.project_name}</b>
          <span className="font-mono text-[11px] text-muted-foreground">
            {task.task_id} · {task.source} · {task.priority}
            {task.worker ? ` · ${task.worker}` : ""}
          </span>
        </div>
        <Badge
          variant={
            task.status === "running"
              ? "rendering"
              : task.status === "succeeded"
                ? "done"
                : task.status === "failed"
                  ? "failed"
                  : "queued"
          }
        >
          {task.status}
        </Badge>
      </div>
      {task.status === "running" && (
        <div className="grid gap-1">
          <div className="h-1.5 overflow-hidden rounded-full bg-border">
            <div
              className="h-full bg-accent-500 transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <span className="font-mono text-[10px] text-muted-foreground">
            {progressPct}% · ETA {Math.round(task.estimated_seconds)}s
          </span>
        </div>
      )}
    </div>
  );
}

function ProjectCard({ project }: { project: RecentProject }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start gap-2">
        <PlayCircle className="mt-0.5 h-4 w-4 text-accent-300" aria-hidden />
        <div className="grid leading-tight">
          <CardTitle className="text-sm">{project.name}</CardTitle>
          <span className="text-[11px] text-muted-foreground">
            {project.purpose} · {project.aspect_ratio} ·{" "}
            {project.duration_seconds}s
          </span>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3">
        <p className="line-clamp-2 text-[11px] text-muted-foreground">
          {project.brief}
        </p>
        <div className="flex items-center justify-between">
          <Badge
            variant={
              project.status === "done" || project.status === "succeeded"
                ? "done"
                : project.status === "rendering"
                  ? "rendering"
                  : "draft"
            }
          >
            {project.status}
          </Badge>
          <span className="text-[10px] text-muted-foreground">
            {new Date(project.updated_at).toLocaleString("zh-CN")}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function Swatch({ label, color }: { label: string; color: string }) {
  return (
    <div className="grid gap-1">
      <div
        className="h-8 rounded-md border border-border"
        style={{ background: color }}
        aria-label={`${label} ${color}`}
      />
      <span className="text-center font-mono text-muted-foreground">
        {label}
      </span>
    </div>
  );
}
