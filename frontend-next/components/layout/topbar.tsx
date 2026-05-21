"use client";

import { Search, Bell, HelpCircle, Sparkles, ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";

const ROUTE_LABEL: Record<string, string> = {
  "/dashboard": "工作台",
  "/create": "新建视频",
  "/projects": "项目库",
  "/templates": "模板",
  "/library": "素材库",
  "/brand": "品牌套件",
  "/team": "团队",
  "/settings": "设置",
};

export function Topbar() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const label = ROUTE_LABEL[`/${segments[0]}`] ?? segments[0];

  return (
    <header className="sticky top-0 z-10 flex h-[60px] items-center gap-4 border-b border-border bg-background/55 px-4 backdrop-blur-md md:px-10">
      <nav className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground" aria-label="面包屑">
        <span className="hidden sm:inline">Acme</span>
        <ChevronRight className="hidden h-3 w-3 opacity-40 sm:block" />
        <b className="truncate font-semibold text-foreground">{label}</b>
        {segments[0] === "projects" && segments[1] && (
          <>
            <ChevronRight className="h-3 w-3 opacity-40" />
            <b className="truncate font-semibold text-foreground">项目 #{decodeURIComponent(segments[1])}</b>
          </>
        )}
        {segments[0] !== "projects" && segments[1] && (
          <>
            <ChevronRight className="h-3 w-3 opacity-40" />
            <b className="truncate font-semibold text-foreground">{decodeURIComponent(segments[1])}</b>
          </>
        )}
      </nav>

      <label className="ml-6 hidden max-w-md flex-1 items-center gap-2 rounded-md border border-border bg-card/70 px-3 py-1.5 text-sm text-muted-foreground focus-within:border-accent-500 focus-within:ring-2 focus-within:ring-accent-500/30 md:flex">
        <Search className="h-3.5 w-3.5" aria-hidden />
        <input
          type="search"
          aria-label="搜索项目、素材、模板"
          placeholder="搜索项目、素材、模板…"
          className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
        />
        <kbd className="rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">⌘K</kbd>
      </label>

      <div className="ml-auto flex items-center gap-2 md:gap-3">
        <Button variant="ghost" size="icon" aria-label="搜索" className="md:hidden">
          <Search className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" aria-label="通知">
          <Bell className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" aria-label="帮助" className="hidden sm:inline-flex">
          <HelpCircle className="h-4 w-4" />
        </Button>
        <Button asChild>
          <Link href="/create">
            <Sparkles className="h-4 w-4" />
            <span className="hidden sm:inline">新建视频</span>
          </Link>
        </Button>
      </div>
    </header>
  );
}
