"use client";

import { Search, Bell, HelpCircle, Sparkles, ChevronRight, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { MobileSidebar } from "./mobile-sidebar";
import { ROUTE_LABEL } from "@/lib/nav";

export function Topbar() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const label = ROUTE_LABEL[`/${segments[0]}`] ?? segments[0];
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    setDrawer(false);
  }, [pathname]);

  return (
    <>
      <header className="sticky top-0 z-20 flex h-[60px] items-center gap-3 border-b border-border/85 bg-background/70 px-4 backdrop-blur-xl md:px-10">
        <Button
          variant="ghost"
          size="icon"
          aria-label={drawer ? "关闭菜单" : "打开菜单"}
          aria-expanded={drawer}
          className="md:hidden"
          onClick={() => setDrawer((d) => !d)}
        >
          {drawer ? <X className="h-4 w-4" aria-hidden /> : <Menu className="h-4 w-4" aria-hidden />}
        </Button>
        <nav className="flex min-w-0 items-center gap-2 text-sm text-muted-foreground" aria-label="面包屑">
          <span className="hidden sm:inline">Acme</span>
          <ChevronRight className="hidden h-3 w-3 opacity-40 sm:block" />
          <b className="truncate font-semibold text-foreground">{label}</b>
          {segments[0] === "projects" && segments[1] && (
            <>
              <ChevronRight className="h-3 w-3 opacity-40" aria-hidden />
              <b className="truncate font-semibold text-foreground">项目 #{decodeURIComponent(segments[1])}</b>
            </>
          )}
          {segments[0] !== "projects" && segments[1] && (
            <>
              <ChevronRight className="h-3 w-3 opacity-40" aria-hidden />
              <b className="truncate font-semibold text-foreground">{decodeURIComponent(segments[1])}</b>
            </>
          )}
        </nav>

        <label className="ml-6 hidden max-w-md flex-1 items-center gap-2 rounded-md border border-border bg-card/65 px-3 py-1.5 text-sm text-muted-foreground transition-colors focus-within:border-accent-500/60 focus-within:bg-card/85 focus-within:shadow-[0_0_0_3px_rgba(34,211,183,0.12)] md:flex">
          <Search className="h-3.5 w-3.5" aria-hidden />
          <input
            type="search"
            aria-label="搜索项目、素材、模板"
            placeholder="搜索项目、素材、模板…"
            className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
          />
          <kbd className="rounded border border-border bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">⌘K</kbd>
        </label>

        <div className="ml-auto flex items-center gap-2 md:gap-3">
          <Button variant="ghost" size="icon" aria-label="搜索" className="md:hidden">
            <Search className="h-4 w-4" aria-hidden />
          </Button>
          <Button variant="ghost" size="icon" asChild className="relative">
            <Link href="/notifications" aria-label="通知 · 3 条未读">
              <Bell className="h-4 w-4" aria-hidden />
              <span
                aria-hidden
                className="absolute right-2 top-2 grid h-3.5 w-3.5 place-items-center rounded-full bg-accent-500 text-[9px] font-bold text-navy-950 num shadow-[0_0_0_2px_hsl(var(--background))]"
              >
                3
              </span>
            </Link>
          </Button>
          <Button variant="ghost" size="icon" aria-label="帮助" className="hidden sm:inline-flex">
            <HelpCircle className="h-4 w-4" aria-hidden />
          </Button>
          <Button asChild>
            <Link href="/create">
              <Sparkles className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">新建视频</span>
            </Link>
          </Button>
        </div>
      </header>
      <MobileSidebar open={drawer} onClose={() => setDrawer(false)} />
    </>
  );
}
