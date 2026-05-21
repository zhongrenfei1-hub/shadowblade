import { Sparkles } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProjectCard } from "@/components/workspace/project-card";

const FILTERS = [
  { id: "all", label: "全部", count: 38 },
  { id: "marketing", label: "营销", count: 16 },
  { id: "training", label: "培训", count: 9 },
  { id: "product_demo", label: "演示", count: 7 },
  { id: "social", label: "社交", count: 6 },
];

export default async function ProjectsPage() {
  const { items } = await api.projects();

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">项目库 · 历史记录</span>
        <div className="flex items-end gap-6">
          <div>
            <h1 className="font-display text-[34px] font-semibold tracking-tight">38 个项目 · 6 个进行中</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              营销侧占 41%。本月平均发布周期 1.4 天。
            </p>
          </div>
          <Button asChild className="ml-auto">
            <Link href="/create">
              <Sparkles className="h-4 w-4" /> 新建视频
            </Link>
          </Button>
        </div>
      </section>

      <Card>
        <div className="flex flex-wrap items-center gap-3 border-b border-border px-6 py-4">
          {FILTERS.map((f, i) => (
            <Button
              key={f.id}
              size="sm"
              variant={i === 0 ? "default" : "outline"}
              className="rounded-full"
            >
              {f.label}
              <span className="ml-1.5 text-[10px] text-muted-foreground">{f.count}</span>
            </Button>
          ))}
          <div className="flex-1" />
          <Button size="sm" variant="outline">状态 · 任意</Button>
          <Button size="sm" variant="outline">负责人 · 任意</Button>
          <Button size="sm" variant="outline">品牌套件 · 任意</Button>
        </div>
        <CardContent className="grid grid-cols-3 gap-4 p-6">
          {items.map((p) => <ProjectCard key={p.id} project={p} />)}
        </CardContent>
      </Card>
    </>
  );
}
