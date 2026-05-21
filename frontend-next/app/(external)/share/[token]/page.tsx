"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Play,
  Pause,
  Check,
  X,
  MessageCircle,
  Volume2,
  Maximize2,
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
import { cn } from "@/lib/utils";

type Comment = {
  id: string;
  who: string;
  initials: string;
  when: string;
  text: string;
  cite?: string;
};

const COMMENTS: Comment[] = [
  { id: "c1", who: "Priya Rao", initials: "PR", when: "3 分钟前", text: '把 "without lifting a wrist" 换成 "无需抬腕"，中国市场测试更顺。', cite: "场景 04 · 字幕 18-22" },
  { id: "c2", who: "Diego Alvarez", initials: "DA", when: "11 分钟前", text: "CTA 段的音乐压得有点低，建议提到 -6 dB。", cite: "音乐 · 0:24 → 0:28" },
];

export default function SharePage({ params }: { params: { token: string } }) {
  const [playing, setPlaying] = useState(false);
  const [decided, setDecided] = useState<"approve" | "reject" | null>(null);
  const [copied, setCopied] = useState(false);
  const [comments, setComments] = useState(COMMENTS);
  const [draft, setDraft] = useState("");

  async function copyLink() {
    const url = typeof window !== "undefined" ? window.location.href : "";
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {}
  }

  function postComment() {
    if (!draft.trim()) return;
    setComments((c) => [
      { id: `c${Date.now()}`, who: "外部审核员", initials: "Y", when: "刚刚", text: draft.trim() },
      ...c,
    ]);
    setDraft("");
  }

  return (
    <div className="min-h-screen bg-background">
      {/* 顶部：品牌 + 信任徽章 + 链接信息 */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3 md:px-6">
          <Link href="/" className="flex items-center gap-2.5" aria-label="ShadowBlade 首页">
            <span className="grid h-7 w-7 place-items-center rounded-md border border-accent-500/30 bg-gradient-to-br from-navy-700 to-navy-900">
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none">
                <path d="M4 4L20 12L4 20V14L12 12L4 10V4Z" fill="url(#sm)" />
                <defs>
                  <linearGradient id="sm" x1="4" y1="4" x2="20" y2="20">
                    <stop offset="0%" stopColor="#22D3B7" />
                    <stop offset="100%" stopColor="#38BDF8" />
                  </linearGradient>
                </defs>
              </svg>
            </span>
            <span className="font-display text-sm font-semibold tracking-tight">ShadowBlade</span>
          </Link>
          <Badge variant="done" className="hidden md:inline-flex">
            <ShieldCheck className="h-3 w-3" />
            签名链接 · 已验证
          </Badge>
          <span className="ml-auto hidden items-center gap-2 text-[11px] text-muted-foreground md:flex">
            <Clock className="h-3 w-3" /> 3 天后失效
          </span>
          <Button variant="outline" size="sm" onClick={copyLink}>
            {copied ? <Check className="h-3.5 w-3.5 text-accent-300" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "已复制" : "复制链接"}
          </Button>
        </div>
      </header>

      <div className="mx-auto grid max-w-5xl gap-6 px-4 py-6 md:px-6 md:py-8">
        <section className="grid gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
            外部审阅 · token {params.token}
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
              <div className="relative aspect-video bg-black">
                <svg viewBox="0 0 800 450" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
                  <defs>
                    <linearGradient id="bgshare" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stopColor="#15376a" />
                      <stop offset="100%" stopColor="#050a18" />
                    </linearGradient>
                    <radialGradient id="glwshare" cx="0.65" cy="0.35" r="0.6">
                      <stop offset="0%" stopColor="rgba(34,211,183,0.4)" />
                      <stop offset="100%" stopColor="rgba(34,211,183,0)" />
                    </radialGradient>
                  </defs>
                  <rect width="800" height="450" fill="url(#bgshare)" />
                  <rect width="800" height="450" fill="url(#glwshare)" />
                  <g transform="translate(500 225)">
                    <circle r="160" fill="none" stroke="rgba(34,211,183,0.25)" strokeWidth="1" strokeDasharray="3 5" />
                    <circle r="100" fill="rgba(34,211,183,0.2)" />
                    <circle r="56" fill="rgba(34,211,183,0.4)" />
                    <circle r="24" fill="#22D3B7" />
                  </g>
                  <text x="60" y="180" fill="#22D3B7" fontFamily="Inter" fontSize="11" letterSpacing="3">
                    ACME · 智能腕环
                  </text>
                  <text x="60" y="226" fill="#F7F9FC" fontFamily="Inter Display" fontSize="38" fontWeight="700">
                    你的一天，准时
                  </text>
                  <text x="60" y="260" fill="#8590A8" fontFamily="Inter" fontSize="14">
                    无需打断节奏。
                  </text>
                </svg>

                {/* 水印 */}
                <span aria-hidden className="pointer-events-none absolute right-4 top-4 select-none rounded border border-white/20 bg-black/40 px-2 py-1 text-[10px] font-bold tracking-wider text-white/70 backdrop-blur-sm">
                  DRAFT · v17
                </span>

                <button
                  type="button"
                  onClick={() => setPlaying((p) => !p)}
                  className="absolute inset-0 grid place-items-center bg-gradient-to-b from-transparent to-black/40 transition-opacity hover:bg-black/20"
                  aria-label={playing ? "暂停" : "播放"}
                >
                  {!playing && (
                    <span className="grid h-16 w-16 place-items-center rounded-full bg-accent-500 text-navy-950 shadow-[0_16px_32px_-8px_rgba(34,211,183,0.5)]">
                      <Play className="h-7 w-7 fill-current" />
                    </span>
                  )}
                </button>

                <div className="absolute inset-x-3 bottom-3 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setPlaying((p) => !p)}
                    className="grid h-9 w-9 place-items-center rounded-full bg-accent-500 text-navy-950"
                    aria-label={playing ? "暂停" : "播放"}
                  >
                    {playing ? <Pause className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 fill-current" />}
                  </button>
                  <time className="font-mono text-xs text-white">0:16</time>
                  <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/20">
                    <span className="absolute inset-y-0 left-0 w-[60%] rounded-full bg-accent-500" />
                  </div>
                  <time className="font-mono text-xs text-white">0:28</time>
                  <Button size="icon" variant="ghost" aria-label="音量" className="text-white hover:bg-white/10">
                    <Volume2 className="h-4 w-4" />
                  </Button>
                  <Button size="icon" variant="ghost" aria-label="全屏" className="text-white hover:bg-white/10">
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
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
                  <Check className="h-4 w-4" />
                  {decided === "approve" ? "已批准" : "批准 v17"}
                </Button>
                <Button
                  size="lg"
                  variant={decided === "reject" ? "destructive" : "outline"}
                  onClick={() => setDecided("reject")}
                  disabled={!!decided}
                >
                  <X className="h-4 w-4" />
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
                    <MessageCircle className="h-3.5 w-3.5" />
                    发表
                  </Button>
                </div>
                <div className="h-px bg-border" />
                {comments.map((c) => (
                  <div key={c.id} className="grid gap-1.5 rounded-md border border-border bg-card/40 p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <Avatar className="h-5 w-5 text-[9px]">
                        <AvatarFallback>{c.initials}</AvatarFallback>
                      </Avatar>
                      <b className="font-semibold">{c.who}</b>
                      <time className="ml-auto font-mono text-[10px] text-muted-foreground">{c.when}</time>
                    </div>
                    <div className="text-muted-foreground">{c.text}</div>
                    {c.cite && <div className="font-mono text-[10px] text-accent-300">{c.cite}</div>}
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Lock className="h-3.5 w-3.5 text-accent-300" />
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
            <Link href="/" className="hover:text-foreground">了解 ShadowBlade</Link>
            <span>·</span>
            <a href="mailto:support@shadowblade.io" className="hover:text-foreground">联系</a>
          </span>
        </div>
      </footer>
    </div>
  );
}
