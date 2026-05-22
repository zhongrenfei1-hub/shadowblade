"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  AtSign,
  Info,
  AlertTriangle,
  XCircle,
  DollarSign,
  Inbox,
  Settings as SettingsIcon,
  CheckCheck,
  Archive,
  AlertCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/marketing/empty-state";
import { cn } from "@/lib/utils";
import {
  archive as archiveNotification,
  getUnreadCount,
  listNotifications,
  markAllRead,
  markRead,
  type NotificationCategory,
  type NotificationKind,
  type NotificationRead,
} from "@/lib/api/notifications";

// ─── 视图层类型 ──────────────────────────────────────────────────────
// 前端 UI 用「Tab」语义；后端用「category」。两者一一对应，加一个 "all"
// 给前端做「不过滤」状态。

type Tab = "all" | NotificationCategory;

const TAB_LABELS: { id: Tab; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "approvals", label: "审批" },
  { id: "mentions", label: "@ 提及" },
  { id: "pipeline", label: "流水线" },
  { id: "drift", label: "品牌偏移" },
  { id: "billing", label: "计费" },
  { id: "system", label: "系统" },
];

const KIND_ICON: Record<NotificationKind, { icon: LucideIcon; cls: string }> = {
  done: { icon: Check, cls: "bg-accent-500/15 text-accent-300" },
  mention: { icon: AtSign, cls: "bg-violet-500/15 text-violet-300" },
  info: { icon: Info, cls: "bg-sky-500/15 text-sky-300" },
  warn: { icon: AlertTriangle, cls: "bg-amber-500/15 text-amber-300" },
  fail: { icon: XCircle, cls: "bg-rose-500/15 text-rose-300" },
  billing: { icon: DollarSign, cls: "bg-graphite-500/30 text-graphite-200" },
};

// ─── 时间格式化（Intl.RelativeTimeFormat）─────────────────────────────
//
// 比 lib/utils.ts 的 relativeTime 更精细：用浏览器原生 RTF 兼顾本地化和单复数。
const RTF = new Intl.RelativeTimeFormat("zh-CN", { numeric: "auto" });

function formatWhen(iso: string): string {
  const date = new Date(iso);
  const diff = (Date.now() - date.getTime()) / 1000; // 秒
  if (diff < 60) return "刚刚";
  if (diff < 3600) return RTF.format(-Math.round(diff / 60), "minute");
  if (diff < 86400) return RTF.format(-Math.round(diff / 3600), "hour");
  if (diff < 604800) return RTF.format(-Math.round(diff / 86400), "day");
  return date.toLocaleDateString("zh-CN");
}

// ─── Fallback：接口失败时撑起 UI（开发体验）─────────────────────────
//
// 与原 mock 对齐，但加上后端形状要求的字段（category / archived / read 等）。
const FALLBACK: NotificationRead[] = [
  {
    id: 1,
    user_id: 1,
    workspace_id: 1,
    type: "video_generated",
    category: "pipeline",
    kind: "done",
    title: "运行 #901 已完成 · 智能腕环",
    message: "混剪 + 渲染共 5 分 38 秒。输出 4K，-14 LUFS。已通知 2 位审核员。",
    payload: {},
    read: false,
    read_at: null,
    archived: false,
    created_at: new Date(Date.now() - 0).toISOString(),
  },
  {
    id: 2,
    user_id: 1,
    workspace_id: 1,
    type: "mention",
    category: "mentions",
    kind: "mention",
    title: "Priya Rao @ 了你",
    message: "「@Ava — 帮看看新片尾？上轮在 TikTok 转化高了约 22%。」",
    payload: {},
    read: false,
    read_at: null,
    archived: false,
    created_at: new Date(Date.now() - 3 * 60_000).toISOString(),
  },
  {
    id: 3,
    user_id: 1,
    workspace_id: 1,
    type: "video_generated",
    category: "pipeline",
    kind: "info",
    title: "运行 #902 已启动 · AI Copilot 演示",
    message: "制作人 Priya Rao · 优先级 高 · gpu-cluster-1 · 预计 2 分 22 秒。",
    payload: {},
    read: false,
    read_at: null,
    archived: false,
    created_at: new Date(Date.now() - 9 * 60_000).toISOString(),
  },
  {
    id: 4,
    user_id: 1,
    workspace_id: 1,
    type: "brand_drift_detected",
    category: "drift",
    kind: "warn",
    title: "品牌偏移 · 2 条成片",
    message: "用了 #20D2B5，应为 #22D3B7。可一键自动修正，下次渲染生效。",
    payload: {},
    read: false,
    read_at: null,
    archived: false,
    created_at: new Date(Date.now() - 22 * 60_000).toISOString(),
  },
  {
    id: 5,
    user_id: 1,
    workspace_id: 1,
    type: "approval_requested",
    category: "approvals",
    kind: "done",
    title: "审核员在等 · 销售工程师训练营",
    message: "Marcus Lee 提交了 96 秒成片审批。品牌套件 Core，偏移评分 0.00。",
    payload: {},
    read: false,
    read_at: null,
    archived: false,
    created_at: new Date(Date.now() - 44 * 60_000).toISOString(),
  },
  {
    id: 6,
    user_id: 1,
    workspace_id: 1,
    type: "video_failed",
    category: "drift",
    kind: "fail",
    title: "配音错配 · 1 条成片",
    message: "Acme · Core 要求灵韵女声，实际用了炽炎男声。重新渲染已排队。",
    payload: {},
    read: true,
    read_at: new Date(Date.now() - 60 * 60_000).toISOString(),
    archived: false,
    created_at: new Date(Date.now() - 2 * 3_600_000).toISOString(),
  },
  {
    id: 7,
    user_id: 1,
    workspace_id: 1,
    type: "billing",
    category: "billing",
    kind: "billing",
    title: "UTC 零点结算",
    message: "本周期已用 387 / 1,000 条渲染。无超额预警。",
    payload: {},
    read: true,
    read_at: new Date(Date.now() - 4 * 3_600_000).toISOString(),
    archived: false,
    created_at: new Date(Date.now() - 5 * 3_600_000).toISOString(),
  },
];

// ─── 页面 ─────────────────────────────────────────────────────────────

export default function NotificationsPage() {
  const [tab, setTab] = useState<Tab>("all");
  const [items, setItems] = useState<NotificationRead[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [usedFallback, setUsedFallback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 拉一次列表 + 未读数。两个端点并行。
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      // 服务端已支持按 category 过滤，但 tab 也包含 "all"。
      // 我们一次性拉全部、前端筛 tab — 这样切 tab 不用再打接口，体验更顺。
      const [list, unread] = await Promise.all([
        listNotifications({ limit: 100, include_archived: false }),
        getUnreadCount(),
      ]);
      setItems(list.items);
      setUnreadCount(unread.unread);
      setUsedFallback(false);
      setError(null);
    } catch (err) {
      // 开发环境：后端没接通 → 用 fallback 撑起 UI，便于设计走查。
      if (process.env.NODE_ENV !== "production") {
        // eslint-disable-next-line no-console
        console.warn("[notifications] 走 fallback：", err);
      }
      setItems(FALLBACK);
      setUnreadCount(FALLBACK.filter((n) => !n.read).length);
      setUsedFallback(true);
      setError(err instanceof Error ? err.message : "拉取失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // 当前 tab 下可见的通知（已过滤归档；归档逻辑由后端控制）。
  const visible = useMemo(
    () => items.filter((n) => tab === "all" || n.category === tab),
    [items, tab],
  );

  // 侧栏 tab 计数实时算 — 不打额外接口。
  const tabs = useMemo(() => {
    return TAB_LABELS.map((t) => ({
      ...t,
      count: t.id === "all" ? items.length : items.filter((n) => n.category === t.id).length,
    }));
  }, [items]);

  // ─── 操作（乐观更新 + 失败时刷一次列表纠偏）───────────────────────

  async function handleMarkRead(id: number) {
    setItems((prev) =>
      prev.map((n) =>
        n.id === id ? { ...n, read: true, read_at: new Date().toISOString() } : n,
      ),
    );
    setUnreadCount((c) => Math.max(0, c - 1));
    if (usedFallback) return; // fallback 模式下不打接口
    try {
      await markRead(id);
    } catch (err) {
      // 失败回滚 — 直接拉一次列表，简单可靠。
      // eslint-disable-next-line no-console
      console.warn("[notifications] markRead 失败：", err);
      void refresh();
    }
  }

  async function handleMarkAllRead() {
    // 仅对当前 tab 全部已读；"all" 时是所有。
    const category = tab === "all" ? undefined : tab;
    setItems((prev) =>
      prev.map((n) => {
        const inScope = category ? n.category === category : true;
        return inScope && !n.read
          ? { ...n, read: true, read_at: new Date().toISOString() }
          : n;
      }),
    );
    setUnreadCount((c) =>
      category
        ? Math.max(0, c - items.filter((n) => n.category === category && !n.read).length)
        : 0,
    );
    if (usedFallback) return;
    try {
      await markAllRead(category);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("[notifications] markAllRead 失败：", err);
      void refresh();
    }
  }

  async function handleArchive(id: number) {
    setItems((prev) => prev.filter((n) => n.id !== id));
    if (usedFallback) return;
    try {
      await archiveNotification(id);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("[notifications] archive 失败：", err);
      void refresh();
    }
  }

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          工作空间 · 收件箱
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              {loading ? "加载中…" : `${unreadCount} 条未读`}
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              流水线事件、审批、品牌偏移告警、@ 提及。本来要去 Slack 翻的东西，都在这一个地方。
            </p>
            {usedFallback && error && (
              <p className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-300">
                <AlertCircle className="h-3 w-3" aria-hidden />
                后端未连通，正在用示例数据。
              </p>
            )}
          </div>
          <div className="flex gap-2 md:gap-3">
            <Button
              variant="outline"
              onClick={handleMarkAllRead}
              disabled={loading || unreadCount === 0}
              aria-label="全部标已读"
            >
              <CheckCheck className="h-3.5 w-3.5" aria-hidden />
              <span className="hidden sm:inline">全部标已读</span>
            </Button>
            <Button variant="outline" aria-label="通知设置">
              <SettingsIcon className="h-3.5 w-3.5" aria-hidden />
              <span className="hidden sm:inline">通知设置</span>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 md:grid-cols-[200px_1fr] items-start">
        {/* aside 保留 complementary landmark 语义；role=toolbar 下移到内层 div 防覆盖。
            见 test ring 004 P1.12 修复（refine 004 引入的副作用）。 */}
        <aside aria-label="通知分类">
          <div className="grid gap-1" role="toolbar" aria-label="通知分类筛选">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                aria-pressed={tab === t.id}
                className={cn(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  tab === t.id
                    ? "bg-accent-500/12 text-foreground"
                    : "text-muted-foreground hover:bg-white/[0.04]",
                )}
              >
                {t.label}
                <span className="ml-auto rounded-full bg-white/[0.06] px-2 py-0.5 text-[11px] num text-muted-foreground">
                  {t.count}
                </span>
              </button>
            ))}
          </div>
        </aside>

        <Card>
          <CardContent className="p-0">
            {loading ? (
              <NotificationSkeleton />
            ) : visible.length === 0 ? (
              <EmptyState
                icon={Inbox}
                title="全部处理完了"
                description="这个分类下没有新的通知。"
              />
            ) : (
              visible.map((n, i) => {
                const { icon: Icon, cls } = KIND_ICON[n.kind];
                const isUnread = !n.read;
                return (
                  <article
                    key={n.id}
                    className={cn(
                      "grid grid-cols-[28px_1fr_auto] items-start gap-3 px-6 py-4",
                      i !== 0 && "border-t border-border",
                      isUnread && "bg-accent-500/[0.02]",
                    )}
                  >
                    <span
                      className={cn(
                        "mt-0.5 grid h-7 w-7 place-items-center rounded-md",
                        cls,
                      )}
                      aria-hidden
                    >
                      <Icon className="h-3.5 w-3.5" aria-hidden />
                    </span>
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold">{n.title}</h3>
                      <p className="mt-0.5 text-sm text-muted-foreground">
                        {n.message}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {isUnread && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleMarkRead(n.id)}
                          >
                            <Check className="h-3 w-3" aria-hidden />
                            标已读
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleArchive(n.id)}
                          aria-label="归档"
                        >
                          <Archive className="h-3 w-3" aria-hidden />
                          归档
                        </Button>
                      </div>
                    </div>
                    <time
                      dateTime={n.created_at}
                      className="font-mono text-[11px] text-muted-foreground whitespace-nowrap"
                      title={new Date(n.created_at).toLocaleString("zh-CN")}
                    >
                      {formatWhen(n.created_at)}
                    </time>
                  </article>
                );
              })
            )}
          </CardContent>
        </Card>
      </section>
    </>
  );
}

// ─── 骨架屏 ─────────────────────────────────────────────────────────
//
// 不引入新依赖，直接用 Tailwind animate-pulse + 灰条。5 行刚好填满一屏。
function NotificationSkeleton() {
  return (
    <div aria-busy="true" aria-label="正在加载通知">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "grid grid-cols-[28px_1fr_auto] items-start gap-3 px-6 py-4",
            i !== 0 && "border-t border-border",
          )}
        >
          <div className="mt-0.5 h-7 w-7 animate-pulse rounded-md bg-white/[0.06]" />
          <div className="min-w-0 space-y-2">
            <div className="h-4 w-2/3 animate-pulse rounded bg-white/[0.06]" />
            <div className="h-3 w-full animate-pulse rounded bg-white/[0.04]" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-white/[0.04]" />
          </div>
          <div className="h-3 w-14 animate-pulse rounded bg-white/[0.04]" />
        </div>
      ))}
    </div>
  );
}
