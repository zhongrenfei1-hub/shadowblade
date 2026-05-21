import Link from "next/link";
import { Play, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const CATEGORY_LABEL: Record<string, string> = {
  marketing: "营销",
  training: "培训",
  product_demo: "产品演示",
  social: "社交",
};

export default async function TemplatesPage() {
  const { items } = await api.templates();

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">模板</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">挑一个开头。</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              64 个生产级模板，已按你的品牌套件预调。每个都能在 5 分钟内出首版。
            </p>
          </div>
          <Button asChild>
            <Link href="/create">
              <Sparkles className="h-4 w-4" /> <span className="hidden sm:inline">新建视频</span><span className="sm:hidden">新建</span>
            </Link>
          </Button>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        {["全部", "营销", "产品演示", "培训", "社交", "入职"].map((f, i) => (
          <Button key={f} size="sm" variant={i === 0 ? "default" : "outline"} className="rounded-full">
            {f}
          </Button>
        ))}
      </div>

      <section className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {items.map((t) => (
          <Card
            key={t.id}
            className="group cursor-pointer overflow-hidden transition-all hover:-translate-y-1 hover:border-accent-500/40 hover:shadow-lg"
          >
            <div className="relative grid h-[200px] place-items-center bg-gradient-to-br from-navy-700 to-navy-900">
              <span className="font-display text-2xl font-semibold text-accent-300/60">{t.name.split("·")[0]}</span>
              <div className="absolute inset-0 grid place-items-center bg-gradient-to-b from-transparent to-black/55 opacity-0 transition-opacity group-hover:opacity-100">
                <span className="grid h-12 w-12 place-items-center rounded-full bg-accent-500 text-navy-950">
                  <Play className="h-5 w-5 fill-current" />
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
        ))}
      </section>
    </>
  );
}
