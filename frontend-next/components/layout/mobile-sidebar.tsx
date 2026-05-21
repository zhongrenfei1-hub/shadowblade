"use client";

import { useEffect, useRef } from "react";
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
import { BrandMark } from "@/components/brand/brand-mark";

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
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;

    // body overflow lock · 保留外部脚本的样式以便清理时还原。
    // 若未来叠开多层 modal，每个 layer 各自 capture prev → cleanup 还原各自的 prev，链式安全。
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // 焦点：打开时移到第一个可聚焦元素，关闭时还焦给 trigger
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const firstFocusable = dialogRef.current?.querySelector<HTMLElement>(
      "a, button, [tabindex]:not([tabindex='-1'])"
    );
    firstFocusable?.focus();

    function getFocusable(): HTMLElement[] {
      if (!dialogRef.current) return [];
      return Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          "a, button, [tabindex]:not([tabindex='-1'])"
        )
      ).filter((el) => !el.hasAttribute("disabled") && el.offsetParent !== null);
    }

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const focusables = getFocusable();
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey);

    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", onKey);
      previouslyFocused?.focus();
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
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="主导航"
        className={cn(
          "absolute left-0 top-0 flex h-full w-[280px] max-w-[85vw] flex-col overflow-y-auto border-r border-border bg-gradient-to-b from-navy-900 to-navy-950 px-4 py-5 transition-transform duration-250 ease-out",
          open ? "translate-x-0" : "-translate-x-full"
        )}
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
                      "group relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium",
                      "text-graphite-200 hover:bg-white/[0.05] hover:text-foreground active:bg-white/[0.07]",
                      active && "bg-gradient-to-r from-accent-500/15 to-transparent text-foreground"
                    )}
                  >
                    {active && (
                      <span className="absolute -left-4 top-2 bottom-2 w-0.5 rounded-full bg-accent-500" aria-hidden />
                    )}
                    <Icon className="h-4 w-4 opacity-90" aria-hidden />
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
