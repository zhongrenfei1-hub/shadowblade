"use client";

/**
 * 右上角通知小铃铛 — 显示未读数 badge，点击跳到 /notifications。
 *
 * 设计：
 * - 自治组件：内部轮询 /notifications/unread-count，不依赖父级注入数据。
 * - 轮询周期 30s，避免给后端造成压力；可被 visibilitychange 暂停（页面隐藏时不打接口）。
 * - 失败静默：badge 隐藏即可，不打扰用户。
 * - 99+ 上限：未读数 > 99 显示「99+」防止 badge 撑爆。
 *
 * 用法：
 *   import { NotificationBell } from "@/components/workspace/notification-bell";
 *   <NotificationBell />
 *
 * 替换 topbar 中现有硬编码的 Bell 块即可。
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getUnreadCount } from "@/lib/api/notifications";

const POLL_INTERVAL_MS = 30_000;

export function NotificationBell() {
  const [unread, setUnread] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setInterval> | null = null;

    async function tick() {
      try {
        const { unread: n } = await getUnreadCount();
        if (!cancelled) setUnread(n);
      } catch {
        // 静默失败 — badge 隐藏即可。
        if (!cancelled) setUnread(null);
      }
    }

    function start() {
      void tick();
      timer = setInterval(tick, POLL_INTERVAL_MS);
    }

    function stop() {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }

    // 页面切到后台时停轮询，回前台立刻拉一次 — 既省接口又保证回来时是最新。
    function onVisibility() {
      if (document.visibilityState === "visible") {
        if (!timer) start();
        else void tick();
      } else {
        stop();
      }
    }

    start();
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  const display = unread === null ? null : unread > 99 ? "99+" : String(unread);
  const ariaLabel =
    unread === null
      ? "通知"
      : unread === 0
        ? "通知 · 无未读"
        : `通知 · ${unread} 条未读`;

  return (
    <Button variant="ghost" size="icon" asChild className="relative">
      <Link href="/notifications" aria-label={ariaLabel}>
        <Bell className="h-4 w-4" aria-hidden />
        {display !== null && unread !== null && unread > 0 && (
          <span
            aria-hidden
            className="absolute right-1.5 top-1.5 grid h-4 min-w-[1rem] place-items-center rounded-full bg-accent-500 px-1 text-[9px] font-bold text-navy-950 num shadow-[0_0_0_2px_hsl(var(--background))]"
          >
            {display}
          </span>
        )}
      </Link>
    </Button>
  );
}
