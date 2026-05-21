import { Sparkles } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ProjectsBoard } from "@/components/workspace/projects-board";

export default async function ProjectsPage() {
  const { items, total } = await api.projects();
  const inProgress = items.filter((p) => ["rendering", "scripting", "storyboard", "review", "running"].includes(p.status)).length;

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">项目库 · 历史记录</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              <span className="num">{total}</span> 个项目 · <span className="num">{inProgress}</span> 个进行中
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              营销侧占 41%。本月平均发布周期 1.4 天。
            </p>
          </div>
          <Button asChild>
            <Link href="/create">
              <Sparkles className="h-4 w-4" /> <span className="hidden sm:inline">新建视频</span><span className="sm:hidden">新建</span>
            </Link>
          </Button>
        </div>
      </section>

      <Card>
        <ProjectsBoard projects={items} />
      </Card>
    </>
  );
}
