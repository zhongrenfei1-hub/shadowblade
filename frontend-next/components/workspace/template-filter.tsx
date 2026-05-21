"use client";

import { useMemo, useState } from "react";
import { Play } from "lucide-react";
import type { Template } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const CATEGORY_LABEL: Record<string, string> = {
  marketing: "营销",
  training: "培训",
  product_demo: "产品演示",
  social: "社交",
};

const FILTERS: { id: "all" | Template["category"]; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "marketing", label: "营销" },
  { id: "product_demo", label: "产品演示" },
  { id: "training", label: "培训" },
  { id: "social", label: "社交" },
];

export function TemplateFilter({ templates }: { templates: Template[] }) {
  const [active, setActive] = useState<(typeof FILTERS)[number]["id"]>("all");

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    map.set("all", templates.length);
    for (const t of templates) {
      map.set(t.category, (map.get(t.category) ?? 0) + 1);
    }
    return map;
  }, [templates]);

  const filtered = useMemo(
    () => (active === "all" ? templates : templates.filter((t) => t.category === active)),
    [active, templates]
  );

  return (
    <>
      <div className="flex flex-wrap gap-2" role="toolbar" aria-label="按分类过滤模板">
        {FILTERS.map((f) => (
          <Button
            key={f.id}
            size="sm"
            variant={active === f.id ? "default" : "outline"}
            className="rounded-full"
            onClick={() => setActive(f.id)}
            aria-pressed={active === f.id}
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
      </div>

      <section className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {filtered.length > 0 ? (
          filtered.map((t) => (
            <Card
              key={t.id}
              className="group cursor-pointer overflow-hidden transition-all duration-200 ease-out animate-fade-up hover:-translate-y-1 hover:border-accent-500/40 hover:shadow-lg"
            >
              <div className="relative grid h-[200px] place-items-center bg-gradient-to-br from-navy-700 to-navy-900">
                <span className="font-display text-2xl font-semibold text-accent-300/60">{t.name.split("·")[0]}</span>
                <div className="absolute inset-0 grid place-items-center bg-gradient-to-b from-transparent to-black/55 opacity-0 transition-opacity group-hover:opacity-100">
                  <span className="grid h-12 w-12 place-items-center rounded-full bg-accent-500 text-navy-950 shadow-[0_8px_24px_-8px_rgba(34,211,183,0.6)]">
                    <Play className="h-5 w-5 fill-current" aria-hidden />
                  </span>
                </div>
                <span className="absolute bottom-2.5 right-2.5 rounded bg-black/65 px-1.5 py-0.5 font-mono text-[10px]">
                  {t.aspect_ratio}
                </span>
              </div>
              <div className="grid gap-1.5 p-4">
                <b className="font-display text-sm font-semibold">{t.name}</b>
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>{CATEGORY_LABEL[t.category]}</span>
                  <span>{t.duration_seconds} 秒 · {t.scenes} 场景</span>
                </div>
              </div>
            </Card>
          ))
        ) : (
          <div className="col-span-full rounded-lg border border-dashed border-border bg-card/30 px-6 py-10 text-center text-sm text-muted-foreground">
            该分类暂无模板 — 换个 tab 试试。
          </div>
        )}
      </section>
    </>
  );
}
