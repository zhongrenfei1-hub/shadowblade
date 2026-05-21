"use client";

import { useEffect, useRef, useState } from "react";
import {
  Check,
  X,
  MessageCircle,
  Copy,
  ShieldCheck,
  Clock,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { BrandMark } from "@/components/brand/brand-mark";
import { VideoPlayer } from "@/components/workspace/video-player";
import { cn } from "@/lib/utils";

type Comment = {
  id: string;
  who: string;
  initials: string;
  when: string;
  whenISO: string;
  text: string;
  cite?: string;
};

const COMMENTS: Comment[] = [
  {
    id: "c1",
    who: "Priya Rao",
    initials: "PR",
    when: "3 分钟前",
    whenISO: "2026-05-21T08:57:00Z",
    text: '把 "without lifting a wrist" 换成 "无需抬腕"，中国市场测试更顺。',
    cite: "场景 04 · 字幕 18-22",
  },
  {
    id: "c2",
    who: "Diego Alvarez",
    initials: "DA",
    when: "11 分钟前",
    whenISO: "2026-05-21T08:49:00Z",
    text: "CTA 段的音乐压得有点低，建议提到 -6 dB。",
    cite: "音乐 · 0:24 → 0:28",
  },
];

export default function SharePage({ params }: { params: { token: string } }) {
  const [decided, setDecided] = useState<"approve" | "reject" | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [comments, setComments] = useState(COMMENTS);
  const [draft, setDraft] = useState("");
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
    },
    [],
  );

  async function copyLink() {
    const url = typeof window !== "undefined" ? window.location.href : "";
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setCopyError(null);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopyError("浏览器拒绝了复制操作");
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopyError(null), 2400);
    }
  }

  function postComment() {
    if (!draft.trim()) return;
    setComments((c) => [
      {
        id: `c${Date.now()}`,
        who: "外部审核员",
        initials: "Y",
        when: "刚刚",
        whenISO: new Date().toISOString(),
        text: draft.trim(),
      },
      ...c,
    ]);
    setDraft("");
  }

  // token 可能 32+ 字符，截短前缀 + 用 monospace + tooltip 给完整值
  const tokenShort =
    params.token.length > 10 ? `${params.token.slice(0, 6)}…` : params.token;

  return (
    <div className="bg-background">
      {/* 顶部：品牌 + 信任徽章 + 链接信息 */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3 md:px-6">
          {/* brand logo 点击跳官网而非 /，避免外部访客踩进 (app) — 见 test ring 002 特殊检查 A */}
          <a
            href="https://shadowblade.io/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2.5"
            aria-label="ShadowBlade 官网"
          >
            <BrandMark className="h-7 w-7" />
            <span className="font-display text-sm font-semibold tracking-tight">ShadowBlade</span>
          </a>
          <Badge variant="done" className="hidden md:inline-flex">
            <ShieldCheck className="h-3 w-3" aria-hidden />
            签名链接 · 已验证
          </Badge>
          <span className="ml-auto hidden items-center gap-2 text-[11px] text-muted-foreground md:flex">
            <Clock className="h-3 w-3" aria-hidden /> 3 天后失效
          </span>
          <Button variant="outline" size="sm" onClick={copyLink} aria-label={copied ? "已复制" : "复制链接"}>
            {copied ? <Check className="h-3.5 w-3.5 text-accent-300" aria-hidden /> : <Copy className="h-3.5 w-3.5" aria-hidden />}
            <span className="hidden sm:inline">{copied ? "已复制" : "复制链接"}</span>
          </Button>
        </div>
        {copyError && (
          <div className="border-t border-rose-500/30 bg-rose-500/[0.06] py-2 text-center text-[11px] text-rose-200">
            {copyError}
          </div>
        )}
      </header>

      <div className="mx-auto grid max-w-5xl gap-6 px-4 py-6 md:px-6 md:py-8">
        <section className="grid gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
            外部审阅 · token <span className="font-mono">{tokenShort}</span>
          </span>
          <h1 className="font-display text-2xl font-semibold tracking-tight md:text-3xl">
            春季产品发布 — 智能腕环 · v17
          </h1>
          <p className="text-sm text-muted-foreground">
            Ava Chen 邀请你审阅这条成片。可以观看、评论、批准或要求修改 — 不需要 ShadowBlade 账号。
          </p>
        </section>

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-[1.6fr_1fr] items-start">
          {/* ── 播放器 ─────────────────────── */}
          <div className="grid gap-4">
            <Card className="overflow-hidden">
              <VideoPlayer watermark="DRAFT · v17" />
            </Card>

            {/* 决定区 · 大按钮 */}
            <Card>
              <CardHeader>
                <CardTitle>你的决定</CardTitle>
                <p className="text-sm text-muted-foreground">还有 2 位审核员，过半同意即发布。</p>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2">
                <Button
                  size="lg"
                  onClick={() => setDecided("approve")}
                  disabled={!!decided}
                  className={cn(decided === "approve" && "bg-accent-400")}
                >
                  <Check className="h-4 w-4" aria-hidden />
                  {decided === "approve" ? "已批准" : "批准 v17"}
                </Button>
                <Button
                  size="lg"
                  variant={decided === "reject" ? "destructive" : "outline"}
                  onClick={() => setDecided("reject")}
                  disabled={!!decided}
                >
                  <X className="h-4 w-4" aria-hidden />
                  {decided === "reject" ? "已要求修改" : "要求修改"}
                </Button>
                {decided && (
                  <div className="sm:col-span-2 rounded-md border border-accent-500/30 bg-accent-500/[0.06] px-3 py-2 text-xs text-accent-200">
                    {decided === "approve" ? "已记录你的批准。Ava Chen 会收到通知。" : "已发回制作人，你的评论会同步过去。"}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* ── 评论 + 信息 ─────────────────── */}
          <div className="grid gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-sm">
                  评论 · {comments.length} 条
                  <Badge variant="default" className="text-[10px]">2 条未解决</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <Textarea
                  rows={3}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="留一句评论 · 可以引用场景或时间点..."
                />
                <div className="flex justify-end">
                  <Button size="sm" onClick={postComment} disabled={!draft.trim()}>
                    <MessageCircle className="h-3.5 w-3.5" aria-hidden />
                    发表
                  </Button>
                </div>
                <div className="h-px bg-border" />
                {comments.map((c) => (
                  <article key={c.id} className="grid gap-1.5 rounded-md border border-border bg-card/40 p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Avatar className="h-5 w-5 text-[9px]">
                        <AvatarFallback>{c.initials}</AvatarFallback>
                      </Avatar>
                      <b className="font-semibold">{c.who}</b>
                      <time dateTime={c.whenISO} className="ml-auto font-mono text-[10px] text-muted-foreground">
                        {c.when}
                      </time>
                    </div>
                    <div className="text-muted-foreground">{c.text}</div>
                    {c.cite && <div className="font-mono text-[10px] text-accent-300">{c.cite}</div>}
                  </article>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Lock className="h-3.5 w-3.5 text-accent-300" aria-hidden />
                  链接信息
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 text-xs">
                {[
                  ["分享者", "Ava Chen"],
                  ["接收者", "外部审核员"],
                  ["失效时间", "2026-05-24 09:00 UTC"],
                  ["水印", "DRAFT · v17"],
                  ["访问", "你是第 1 位"],
                  ["下载", "已禁用"],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-border/50 py-1 last:border-0">
                    <span className="text-muted-foreground">{k}</span>
                    <span className="font-mono text-foreground">{v}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </section>
      </div>

      <footer className="border-t border-border bg-background/60 py-6">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 px-4 text-xs text-muted-foreground md:px-6">
          <span>© ShadowBlade · 企业级 AI 视频云</span>
          <span className="ml-auto flex items-center gap-3">
            {/* 外部访客点 footer 不再踩进 (app) — 去官网 */}
            <a
              href="https://shadowblade.io/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground"
            >
              了解 ShadowBlade
            </a>
            <span aria-hidden>·</span>
            <a href="mailto:support@shadowblade.io" className="hover:text-foreground">联系</a>
          </span>
        </div>
      </footer>
    </div>
  );
}
