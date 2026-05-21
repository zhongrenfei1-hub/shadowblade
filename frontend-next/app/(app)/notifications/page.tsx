"use client";

import { useState } from "react";
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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/marketing/empty-state";
import { cn } from "@/lib/utils";

type Kind = "done" | "mention" | "info" | "warn" | "fail" | "billing";
type Tab = "all" | "approvals" | "mentions" | "pipeline" | "drift" | "billing";

type Notice = {
  id: string;
  kind: Kind;
  tab: Tab;
  title: string;
  body: string;
  when: string;
  unread?: boolean;
  actions?: { label: string; primary?: boolean }[];
};

const NOTICES: Notice[] = [
  { id: "n1", kind: "done", tab: "pipeline", title: "运行 #901 已完成 · 智能腕环", body: "混剪 + 渲染共 5 分 38 秒。输出 4K，-14 LUFS。已通知 2 位审核员。", when: "刚刚", unread: true, actions: [{ label: "在编辑器中打开", primary: true }, { label: "批准" }] },
  { id: "n2", kind: "mention", tab: "mentions", title: "Priya Rao @ 了你", body: '「@Ava — 帮看看新片尾？上轮在 TikTok 转化高了约 22%。」', when: "3 分钟前", unread: true, actions: [{ label: "打开评论串" }] },
  { id: "n3", kind: "info", tab: "pipeline", title: "运行 #902 已启动 · AI Copilot 演示", body: "制作人 Priya Rao · 优先级 高 · gpu-cluster-1 · 预计 2 分 22 秒。", when: "9 分钟前", unread: true },
  { id: "n4", kind: "warn", tab: "drift", title: "品牌偏移 · 2 条成片", body: "用了 #20D2B5，应为 #22D3B7。可一键自动修正，下次渲染生效。", when: "22 分钟前", unread: true, actions: [{ label: "应用修复", primary: true }, { label: "查看成片" }] },
  { id: "n5", kind: "done", tab: "approvals", title: "审核员在等 · 销售工程师训练营", body: "Marcus Lee 提交了 96 秒成片审批。品牌套件 Core，偏移评分 0.00。", when: "44 分钟前", unread: true, actions: [{ label: "去审核", primary: true }] },
  { id: "n6", kind: "fail", tab: "drift", title: "配音错配 · 1 条成片", body: "Acme · Core 要求灵韵女声，实际用了炽炎男声。重新渲染已排队。", when: "2 小时前" },
  { id: "n7", kind: "billing", tab: "billing", title: "UTC 零点结算", body: "本周期已用 387 / 1,000 条渲染。无超额预警。", when: "5 小时前" },
  { id: "n8", kind: "info", tab: "pipeline", title: "Worker gpu-cluster-4 已预热", body: "无队列，空闲 12 秒。8 分钟内未被领走会自动伸缩。", when: "昨天" },
];

const TABS: { id: Tab; label: string; count: number }[] = [
  { id: "all", label: "全部", count: NOTICES.length },
  { id: "approvals", label: "审批", count: NOTICES.filter((n) => n.tab === "approvals").length },
  { id: "mentions", label: "@ 提及", count: NOTICES.filter((n) => n.tab === "mentions").length },
  { id: "pipeline", label: "流水线", count: NOTICES.filter((n) => n.tab === "pipeline").length },
  { id: "drift", label: "品牌偏移", count: NOTICES.filter((n) => n.tab === "drift").length },
  { id: "billing", label: "计费", count: NOTICES.filter((n) => n.tab === "billing").length },
];

const KIND_ICON: Record<Kind, { icon: typeof Check; cls: string }> = {
  done: { icon: Check, cls: "bg-accent-500/15 text-accent-300" },
  mention: { icon: AtSign, cls: "bg-violet-500/15 text-violet-300" },
  info: { icon: Info, cls: "bg-sky-500/15 text-sky-300" },
  warn: { icon: AlertTriangle, cls: "bg-amber-500/15 text-amber-300" },
  fail: { icon: XCircle, cls: "bg-rose-500/15 text-rose-300" },
  billing: { icon: DollarSign, cls: "bg-graphite-500/30 text-graphite-200" },
};

export default function NotificationsPage() {
  const [tab, setTab] = useState<Tab>("all");
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const visible = NOTICES.filter((n) => !dismissed.has(n.id)).filter((n) => tab === "all" || n.tab === tab);
  const unreadCount = NOTICES.filter((n) => n.unread && !dismissed.has(n.id)).length;

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">工作空间 · 收件箱</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">{unreadCount} 条未读</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              流水线事件、审批、品牌偏移告警、@ 提及。本来要去 Slack 翻的东西，都在这一个地方。
            </p>
          </div>
          <div className="flex gap-2 md:gap-3">
            <Button variant="outline" onClick={() => setDismissed(new Set(NOTICES.map((n) => n.id)))}>
              <CheckCheck className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">全部标已读</span>
            </Button>
            <Button variant="outline">
              <SettingsIcon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">通知设置</span>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 md:grid-cols-[200px_1fr] items-start">
        <aside className="grid gap-1" aria-label="通知分类">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              aria-current={tab === t.id ? "page" : undefined}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                tab === t.id ? "bg-accent-500/12 text-foreground" : "text-muted-foreground hover:bg-white/[0.04]"
              )}
            >
              {t.label}
              <span className="ml-auto rounded-full bg-white/[0.06] px-2 py-0.5 text-[11px] num text-muted-foreground">
                {t.count}
              </span>
            </button>
          ))}
        </aside>

        <Card>
          <CardContent className="p-0">
            {visible.length === 0 ? (
              <div className="grid place-items-center py-16">
                <EmptyState
                  icon={Inbox}
                  title="全部处理完了"
                  description="这个分类下没有新的通知。"
                />
              </div>
            ) : (
              visible.map((n, i) => {
                const { icon: Icon, cls } = KIND_ICON[n.kind];
                return (
                  <article
                    key={n.id}
                    className={cn(
                      "grid grid-cols-[28px_1fr_auto] items-start gap-3 px-6 py-4",
                      i !== 0 && "border-t border-border",
                      n.unread && "bg-accent-500/[0.022]"
                    )}
                  >
                    <span className={cn("mt-0.5 grid h-7 w-7 place-items-center rounded-md", cls)} aria-hidden>
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold">{n.title}</div>
                      <div className="mt-0.5 text-sm text-muted-foreground">{n.body}</div>
                      {n.actions && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {n.actions.map((a) => (
                            <Button key={a.label} size="sm" variant={a.primary ? "default" : "outline"}>{a.label}</Button>
                          ))}
                        </div>
                      )}
                    </div>
                    <time className="font-mono text-[11px] text-muted-foreground whitespace-nowrap">{n.when}</time>
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
