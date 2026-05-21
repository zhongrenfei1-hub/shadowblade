"use client";

import { useMemo, useState } from "react";
import type { Project } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { CardContent } from "@/components/ui/card";
import { ProjectCard } from "./project-card";

const FILTERS: { id: "all" | Project["purpose"]; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "marketing", label: "营销" },
  { id: "training", label: "培训" },
  { id: "product_demo", label: "演示" },
  { id: "social", label: "社交" },
];

export function ProjectsBoard({ projects }: { projects: Project[] }) {
  const [active, setActive] = useState<(typeof FILTERS)[number]["id"]>("all");
  const [status, setStatus] = useState<string>("any");
  const [owner, setOwner] = useState<string>("any");

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    map.set("all", projects.length);
    for (const p of projects) {
      map.set(p.purpose, (map.get(p.purpose) ?? 0) + 1);
    }
    return map;
  }, [projects]);

  const owners = useMemo(() => {
    const set = new Set(projects.map((p) => p.owner));
    return Array.from(set);
  }, [projects]);

  const filtered = useMemo(() => {
    return projects.filter((p) => {
      if (active !== "all" && p.purpose !== active) return false;
      if (status !== "any" && p.status !== status) return false;
      if (owner !== "any" && p.owner !== owner) return false;
      return true;
    });
  }, [projects, active, status, owner]);

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3 sm:gap-3 sm:px-6 sm:py-4" role="tablist" aria-label="按用途筛选">
        {FILTERS.map((f) => (
          <Button
            key={f.id}
            size="sm"
            variant={active === f.id ? "default" : "outline"}
            className="rounded-full"
            onClick={() => setActive(f.id)}
            role="tab"
            aria-selected={active === f.id}
          >
            {f.label}
            <span
              className={
                active === f.id
                  ? "ml-1 rounded bg-navy-950/25 px-1 text-[10px] num"
                  : "ml-1 rounded bg-white/[0.06] px-1 text-[10px] text-muted-foreground num"
              }
            >
              {counts.get(f.id) ?? 0}
            </span>
          </Button>
        ))}
        <div className="flex-1" />
        <select
          aria-label="按状态过滤"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="hidden h-8 rounded-md border border-input bg-card/60 px-2 text-xs transition-colors hover:border-border focus-visible:border-accent-500/60 focus-visible:bg-card/85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/25 sm:inline-flex"
        >
          <option value="any">状态 · 任意</option>
          <option value="rendering">渲染中</option>
          <option value="review">待审核</option>
          <option value="done">已完成</option>
          <option value="draft">草稿</option>
        </select>
        <select
          aria-label="按负责人过滤"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          className="hidden h-8 rounded-md border border-input bg-card/60 px-2 text-xs transition-colors hover:border-border focus-visible:border-accent-500/60 focus-visible:bg-card/85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/25 sm:inline-flex"
        >
          <option value="any">负责人 · 任意</option>
          {owners.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      </div>
      <CardContent className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 sm:p-6 lg:grid-cols-3">
        {filtered.length > 0 ? (
          filtered.map((p) => (
            <div key={p.id} className="animate-fade-up">
              <ProjectCard project={p} />
            </div>
          ))
        ) : (
          <div className="col-span-full rounded-lg border border-dashed border-border bg-card/30 px-6 py-10 text-center text-sm text-muted-foreground">
            没有匹配项 — 试着放宽筛选条件。
          </div>
        )}
      </CardContent>
    </>
  );
}
