"use client";

import { useEffect } from "react";
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

const NAV = [
  {
    group: "制作",
    items: [
      { href: "/dashboard", label: "工作台", icon: LayoutDashboard },
      { href: "/create", label: "新建视频", icon: Sparkles, cta: true },
      { href: "/projects", label: "项目库", icon: FolderOpen },
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

export function MobileSidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  return (
    <div
      aria-hidden={!open}
      className={cn(
        "fixed inset-0 z-50 md:hidden",
        open ? "pointer-events-auto" : "pointer-events-none"
      )}
    >
      <div
        onClick={onClose}
        className={cn(
          "absolute inset-0 bg-navy-950/70 backdrop-blur-sm transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0"
        )}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="主导航"
        className={cn(
          "absolute left-0 top-0 flex h-full w-[280px] max-w-[85vw] flex-col overflow-y-auto border-r border-border bg-gradient-to-b from-navy-900 to-navy-950 px-4 py-5 transition-transform duration-250 ease-out",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <Link href="/dashboard" className="flex items-center gap-3 px-2 py-2" aria-label="ShadowBlade 首页">
          <span className="grid h-8 w-8 place-items-center rounded-md border border-accent-500/30 bg-gradient-to-br from-navy-700 to-navy-900 shadow-[0_4px_12px_rgba(34,211,183,0.18)]">
            <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" aria-hidden>
              <path d="M4 4L20 12L4 20V14L12 12L4 10V4Z" fill="url(#sb-mark-m)" />
              <defs>
                <linearGradient id="sb-mark-m" x1="4" y1="4" x2="20" y2="20">
                  <stop offset="0%" stopColor="#22D3B7" />
                  <stop offset="100%" stopColor="#38BDF8" />
                </linearGradient>
              </defs>
            </svg>
          </span>
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
                      "group relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium",
                      "text-graphite-200 hover:bg-white/[0.05] hover:text-foreground active:bg-white/[0.07]",
                      active && "bg-gradient-to-r from-accent-500/15 to-transparent text-foreground"
                    )}
                  >
                    {active && (
                      <span className="absolute -left-4 top-2 bottom-2 w-0.5 rounded-full bg-accent-500" aria-hidden />
                    )}
                    <Icon className="h-4 w-4 opacity-90" />
                    <span>{item.label}</span>
                    {item.cta && (
                      <Zap className="ml-auto h-3 w-3 fill-accent-500 text-accent-500" aria-hidden />
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="mt-6 rounded-lg border border-border bg-navy-900/55 p-3">
          <div className="flex items-center gap-3">
            <div className="relative grid h-9 w-9 place-items-center rounded-md bg-gradient-to-br from-navy-700 to-navy-900 text-xs font-bold text-accent-300 dot-online">
              AC
            </div>
            <div className="flex min-w-0 flex-col leading-tight">
              <b className="truncate text-sm">Acme · 规模版</b>
              <span className="truncate text-[11px] text-muted-foreground">24 席 · 管理员</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
