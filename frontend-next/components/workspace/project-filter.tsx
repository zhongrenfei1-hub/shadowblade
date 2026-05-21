"use client";

import { useMemo, useState } from "react";
import type { Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ProjectCard } from "./project-card";

const FILTERS: { id: "all" | Project["purpose"]; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "marketing", label: "营销" },
  { id: "training", label: "培训" },
  { id: "product_demo", label: "演示" },
  { id: "social", label: "社交" },
];

export function ProjectFilter({ projects }: { projects: Project[] }) {
  const [active, setActive] = useState<(typeof FILTERS)[number]["id"]>("all");

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    map.set("all", projects.length);
    for (const p of projects) {
      map.set(p.purpose, (map.get(p.purpose) ?? 0) + 1);
    }
    return map;
  }, [projects]);

  const filtered = useMemo(
    () => (active === "all" ? projects : projects.filter((p) => p.purpose === active)),
    [active, projects]
  );

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="按用途筛选">
        {FILTERS.map((f) => (
          <Button
            key={f.id}
            size="sm"
            variant={active === f.id ? "default" : "outline"}
            onClick={() => setActive(f.id)}
            role="tab"
            aria-selected={active === f.id}
            className="gap-1.5"
          >
            {f.label}
            <span
              className={
                active === f.id
                  ? "rounded bg-navy-950/25 px-1.5 text-[10px] font-semibold num"
                  : "rounded bg-white/[0.06] px-1.5 text-[10px] num text-muted-foreground"
              }
            >
              {counts.get(f.id) ?? 0}
            </span>
          </Button>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.length > 0 ? (
          filtered.map((p) => (
            <div key={p.id} className="animate-fade-up">
              <ProjectCard project={p} />
            </div>
          ))
        ) : (
          <div className="col-span-full rounded-lg border border-dashed border-border bg-card/30 px-6 py-10 text-center text-sm text-muted-foreground">
            该分类暂无项目，换一个 tab 试试。
          </div>
        )}
      </div>
    </div>
  );
}
