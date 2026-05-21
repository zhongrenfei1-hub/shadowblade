"use client";

import { useEffect, useRef, useState } from "react";
import { MessageSquare, AtSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge } from "@/components/workspace/status-badge";
import { cn } from "@/lib/utils";

const COMMENTS = [
  { who: "Priya Rao", presence: "online" as const, when: "3 分钟前", whenISO: "2026-05-21T08:57:00Z", text: '把 "without lifting a wrist" 换成 "无需抬腕"，中国市场测试更顺。', cite: "场景 04 · 字幕 18-22", thread: 2 },
  { who: "Diego Alvarez", presence: "idle" as const, when: "11 分钟前", whenISO: "2026-05-21T08:49:00Z", text: "CTA 段的音乐压得有点低，建议提到 -6 dB。", cite: "音乐 · 0:24 → 0:28", thread: 0 },
];

const PRESENCE_DOT: Record<string, string> = {
  online: "bg-accent-400 shadow-[0_0_6px_rgba(34,211,183,0.55)]",
  idle: "bg-amber-400",
  offline: "bg-graphite-300/60",
};

const VERSIONS = [
  { v: "v17", title: "加急渲染 · Priya 的 CTA 文案", who: "Ava Chen · 4 分钟前", current: true },
  { v: "v16", title: "音乐压低到 -6 dB", who: "Diego Alvarez · 28 分钟前" },
  { v: "v15", title: "片尾卡片替换", who: "Marcus Lee · 1 小时前" },
  { v: "v14", title: "Diego 批准", who: "Diego Alvarez · 4 小时前" },
];

const META: [string, React.ReactNode][] = [
  ["状态", <StatusBadge key="s" status="rendering" />],
  ["简报", "春季智能腕环新品上市"],
  ["模板", "发布主推 v3.1"],
  ["品牌套件", "Acme · 核心版 v3"],
  ["画幅", "9:16 · 1080×1920 · 60 fps · H.264 high"],
  ["时长", "28.0 秒 · 6 个场景"],
  ["配音", "灵韵 · 女声 · -14 LUFS"],
  ["负责人", "Ava Chen"],
  ["审核员", "Priya Rao · Diego Alvarez"],
];

export function MetaTabs() {
  return (
    <Tabs defaultValue="meta">
      <TabsList className="w-full">
        <TabsTrigger value="meta" className="flex-1">概况</TabsTrigger>
        <TabsTrigger value="comments" className="flex-1">评论 ({COMMENTS.length})</TabsTrigger>
        <TabsTrigger value="versions" className="flex-1">版本 (17)</TabsTrigger>
      </TabsList>

      <TabsContent value="meta" className="mt-4 grid gap-2 text-sm">
        <dl className="grid gap-1.5">
          {META.map(([k, v]) => (
            <div key={k as string} className="grid grid-cols-[100px_1fr] gap-3 py-1.5">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="text-foreground">{v}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-3 grid gap-1.5 rounded-md bg-card/50 p-3 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">品牌偏移评分</span>
            <span className="font-mono text-accent-300">0.02 · 远低于 0.10 阈值</span>
          </div>
          <Progress value={2} className="h-1" />
        </div>
      </TabsContent>

      <TabsContent value="comments" className="mt-4 grid gap-3">
        {COMMENTS.map((c) => (
          <div key={c.cite} className="grid gap-2 rounded-md border border-border bg-card/40 p-3 text-sm transition-colors hover:border-accent-500/25">
            <div className="flex items-center gap-2">
              <div className="relative shrink-0">
                <Avatar className="h-6 w-6 text-[10px]">
                  <AvatarFallback>{c.who.split(" ").map((s) => s[0]).join("").slice(0, 2)}</AvatarFallback>
                </Avatar>
                <span
                  aria-hidden
                  className={cn(
                    "absolute bottom-0 right-0 h-2 w-2 translate-x-1/3 translate-y-1/3 rounded-full ring-2 ring-card",
                    PRESENCE_DOT[c.presence]
                  )}
                />
                <span className="sr-only">{c.who} · {c.presence === "online" ? "在线" : c.presence === "idle" ? "离开" : "离线"}</span>
              </div>
              <b className="font-semibold">{c.who}</b>
              {c.thread > 0 && (
                <span className="rounded-full bg-accent-500/12 px-1.5 py-0.5 text-[9px] font-semibold text-accent-300">
                  {c.thread} 条回复
                </span>
              )}
              <time dateTime={c.whenISO} className="ml-auto font-mono text-[10px] text-muted-foreground">{c.when}</time>
            </div>
            <div className="text-muted-foreground">{c.text}</div>
            <div className="inline-flex items-center gap-1 font-mono text-[10px] text-accent-300">
              <span className="h-1 w-1 rounded-full bg-accent-400" aria-hidden />
              {c.cite}
            </div>
          </div>
        ))}
        <CommentComposer />
      </TabsContent>

      <TabsContent value="versions" className="mt-4 grid gap-2">
        {VERSIONS.map((r) => (
          <div
            key={r.v}
            className={cn(
              "grid grid-cols-[60px_1fr_auto] items-center gap-3 rounded-md border border-border bg-card/50 p-3 transition-colors",
              r.current && "border-sky-500/30 bg-sky-500/[0.05]"
            )}
          >
            <div className="text-center font-mono text-sm font-bold text-accent-300">{r.v}</div>
            <div className="min-w-0">
              <div className="text-sm font-semibold">{r.title}</div>
              <div className="truncate text-[11px] text-muted-foreground">{r.who}</div>
            </div>
            {r.current ? <Badge variant="rendering">当前</Badge> : <Button size="sm" variant="outline">恢复</Button>}
          </div>
        ))}
      </TabsContent>
    </Tabs>
  );
}

function CommentComposer() {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const remaining = 500 - text.length;
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  function send() {
    if (!text.trim()) return;
    setSending(true);
    timerRef.current = setTimeout(() => {
      setSending(false);
      setText("");
    }, 600);
  }

  const remainColor = remaining < 0
    ? "text-rose-300"
    : remaining < 50
    ? "text-amber-300"
    : "text-muted-foreground";

  return (
    <div className="grid gap-2">
      <Textarea
        rows={3}
        placeholder="回复，或 @ 提及制作人…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={500}
      />
      <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <AtSign className="h-3 w-3" aria-hidden />
          支持 @ 提及 · ⌘+Enter 发送
        </span>
        <span className={cn("num", remainColor)}>{remaining}</span>
      </div>
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" disabled={!text.trim()}>保存草稿</Button>
        <Button size="sm" onClick={send} disabled={!text.trim() || sending}>
          <MessageSquare className="h-3.5 w-3.5" aria-hidden /> {sending ? "发送中…" : "发送"}
        </Button>
      </div>
    </div>
  );
}
