import Link from "next/link";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { TemplateFilter } from "@/components/workspace/template-filter";

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
              <span className="num">{items.length}</span> 个生产级模板，已按你的品牌套件预调。每个都能在 5 分钟内出首版。
            </p>
          </div>
          <Button asChild>
            <Link href="/create">
              <Sparkles className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">新建视频</span><span className="sm:hidden">新建</span>
            </Link>
          </Button>
        </div>
      </section>

      <TemplateFilter templates={items} />
    </>
  );
}
