"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Sparkles,
  FolderOpen,
  Library,
  Palette,
  LayoutTemplate,
  Users,
  Settings,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";
import { BrandMark } from "@/components/brand/brand-mark";

const NAV = [
  {
    group: "制作",
    items: [
      { href: "/dashboard", label: "工作台", icon: LayoutDashboard },
      {
        href: "/create",
        label: "新建视频",
        icon: Sparkles,
        cta: true,
      },
      { href: "/projects", label: "项目库", icon: FolderOpen, badge: "38" },
      { href: "/templates", label: "模板", icon: LayoutTemplate },
    ],
  },
  {
    group: "素材与品牌",
    items: [
      { href: "/library", label: "素材库", icon: Library },
      { href: "/brand", label: "品牌套件", icon: Palette },
    ],
  },
  {
    group: "工作空间",
    items: [
      { href: "/team", label: "团队", icon: Users },
      { href: "/settings", label: "设置", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside
      aria-label="主导航"
      className="sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col overflow-y-auto border-r border-border bg-gradient-to-b from-navy-900/95 to-navy-950/95 px-3 py-5 backdrop-blur-md md:flex"
    >
      <Link href="/dashboard" className="flex items-center gap-3 px-2 py-2" aria-label="ShadowBlade 首页">
        <BrandMark />
        <span className="flex flex-col">
          <b className="font-display text-sm tracking-tight">ShadowBlade</b>
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">视频云</span>
        </span>
      </Link>

      <nav className="mt-6 flex flex-1 flex-col gap-1">
        {NAV.map((group) => (
          <div key={group.group} className="flex flex-col gap-0.5">
            <div className="px-3 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              {group.group}
            </div>
            {group.items.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    "text-graphite-200 hover:bg-white/[0.04] hover:text-foreground",
                    active && "bg-gradient-to-r from-accent-500/15 to-transparent text-foreground",
                    item.cta && !active && "text-accent-300 hover:bg-accent-500/10"
                  )}
                >
                  {active && (
                    <span className="absolute -left-3 top-2 bottom-2 w-0.5 rounded-full bg-accent-500" aria-hidden />
                  )}
                  <Icon className="h-4 w-4 opacity-90" />
                  <span>{item.label}</span>
                  {item.cta && (
                    <Zap className="ml-auto h-3 w-3 fill-accent-500 text-accent-500" aria-hidden />
                  )}
                  {item.badge && (
                    <span className="ml-auto rounded-full bg-white/5 px-2 py-0.5 text-[11px] num text-muted-foreground">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="mt-6 rounded-lg border border-border bg-navy-900/55 p-3 hairline">
        <div className="flex items-center gap-3">
          <div className="relative grid h-8 w-8 place-items-center rounded-md bg-gradient-to-br from-navy-700 to-navy-900 text-xs font-bold text-accent-300 dot-online">
            AC
          </div>
          <div className="flex min-w-0 flex-col leading-tight">
            <b className="truncate text-sm">Acme · 规模版</b>
            <span className="truncate text-[11px] text-muted-foreground">24 席 · 管理员</span>
          </div>
        </div>
        <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
          <span>本月渲染配额</span>
          <span className="num">
            <b className="text-foreground">387</b> / 1,000
          </span>
        </div>
        <Progress value={38.7} className="mt-1.5 h-1" />
      </div>
    </aside>
  );
}
