"use client";

import { useState } from "react";
import {
  Play,
  Pause,
  Download,
  Share2,
  Copy,
  Check,
  MessageSquare,
  Archive,
  Sparkles,
  Globe,
  Maximize2,
  Volume2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { StatusBadge } from "@/components/workspace/status-badge";

const SCENES = [
  { i: "01", t: "冷开场", dur: "4.0", state: "succeeded" as const },
  { i: "02", t: "产品主视觉", dur: "5.0", state: "succeeded" as const },
  { i: "03", t: "屏幕细节", dur: "4.5", state: "succeeded" as const },
  { i: "04", t: "生活场景", dur: "5.0", state: "succeeded" as const },
  { i: "05", t: "续航 + 轻触", dur: "5.0", state: "succeeded" as const },
  { i: "06", t: "行动号召", dur: "4.5", state: "succeeded" as const },
];

const COMMENTS = [
  { who: "Priya Rao", when: "3 分钟前", text: '把 "without lifting a wrist" 换成 "无需抬腕"，中国市场测试更顺。', cite: "场景 04 · 字幕 18-22" },
  { who: "Diego Alvarez", when: "11 分钟前", text: "CTA 段的音乐压得有点低，建议提到 -6 dB。", cite: "音乐 · 0:24 → 0:28" },
];

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const [playing, setPlaying] = useState(false);
  const [copied, setCopied] = useState(false);
  const shareUrl = `https://review.shadowblade.io/r/${params.id}/q7M2xs9`;

  async function copyShare() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {}
  }

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          项目 #{params.id} · 营销 · 9:16 · 28 秒
        </span>
        <div className="flex items-end gap-6">
          <div>
            <h1 className="font-display text-[34px] font-semibold tracking-tight">春季产品发布 — 智能腕环</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              v17 / 17 · 4 分钟前由 Ava Chen 渲染 · Acme · 核心品牌套件 · 灵韵女声配音
            </p>
          </div>
          <div className="ml-auto flex gap-3">
            <Button variant="outline">
              <Archive className="h-4 w-4" /> 归档
            </Button>
            <Button>
              <Check className="h-4 w-4" /> 批准并发布
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-[1.4fr_1fr] gap-6 items-start">
        {/* ── 左：播放器 + 时间线 ─── */}
        <div className="grid gap-6">
          <Card className="overflow-hidden">
            <div className="relative aspect-video bg-black">
              <svg viewBox="0 0 800 450" preserveAspectRatio="xMidYMid slice" className="h-full w-full">
                <defs>
                  <linearGradient id="prevbg" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#15376a" />
                    <stop offset="100%" stopColor="#050a18" />
                  </linearGradient>
                  <radialGradient id="prevglow" cx="0.65" cy="0.35" r="0.6">
                    <stop offset="0%" stopColor="rgba(34,211,183,0.4)" />
                    <stop offset="100%" stopColor="rgba(34,211,183,0)" />
                  </radialGradient>
                </defs>
                <rect width="800" height="450" fill="url(#prevbg)" />
                <rect width="800" height="450" fill="url(#prevglow)" />
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

              <div className="absolute bottom-3 left-3 right-3 flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setPlaying((p) => !p)}
                  className="grid h-9 w-9 place-items-center rounded-full bg-accent-500 text-navy-950"
                  aria-label={playing ? "暂停" : "播放"}
                >
                  {playing ? <Pause className="h-4 w-4 fill-current" /> : <Play className="h-4 w-4 fill-current" />}
                </button>
                <time className="font-mono text-xs text-white">0:16.8</time>
                <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/20">
                  <span className="absolute inset-y-0 left-0 w-[60%] rounded-full bg-accent-500" />
                </div>
                <time className="font-mono text-xs text-white">0:28.0</time>
                <Button size="icon" variant="ghost" aria-label="音量" className="text-white hover:bg-white/10">
                  <Volume2 className="h-4 w-4" />
                </Button>
                <Button size="icon" variant="ghost" aria-label="全屏" className="text-white hover:bg-white/10">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 border-t border-border bg-card/60 px-5 py-3">
              <Button>
                <Download className="h-4 w-4" /> 下载 MP4
              </Button>
              <Button variant="outline">
                <Share2 className="h-4 w-4" /> 分享给审核员
              </Button>
              <Button variant="outline">
                <Globe className="h-4 w-4" /> 翻译成 5 语言
              </Button>
              <Button variant="outline">
                <Sparkles className="h-4 w-4" /> 再渲染一版
              </Button>
              <div className="ml-auto font-mono text-xs text-muted-foreground">
                1080×1920 · H.264 · 60 fps · 8.4 MB
              </div>
            </div>
          </Card>

          {/* 分享链接卡片 */}
          <Card>
            <CardHeader>
              <CardTitle>分享链接</CardTitle>
              <p className="text-sm text-muted-foreground">
                无需 ShadowBlade 账号即可观看 · 链接 3 天后失效 · 每次访问都记录在审计日志。
              </p>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="flex items-center gap-2">
                <Input value={shareUrl} readOnly className="font-mono text-xs" />
                <Button variant="outline" onClick={copyShare}>
                  {copied ? <Check className="h-4 w-4 text-accent-300" /> : <Copy className="h-4 w-4" />}
                  {copied ? "已复制" : "复制"}
                </Button>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs text-muted-foreground">
                <span>有效期：<b className="text-foreground">2026-05-24</b></span>
                <span>水印：<b className="text-foreground">DRAFT · v17</b></span>
                <span>访问：<b className="text-foreground">2 人 · 0 次下载</b></span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>场景 · 6 个</CardTitle>
              <Button variant="outline" size="sm">在编辑器中打开</Button>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-6 gap-3">
                {SCENES.map((s) => (
                  <div key={s.i} className="overflow-hidden rounded-md border border-border bg-card/50">
                    <div className="grid h-[70px] place-items-center bg-gradient-to-br from-navy-700 to-navy-900 font-mono text-[10px] text-muted-foreground">
                      {s.i}
                    </div>
                    <div className="grid gap-0.5 p-2">
                      <b className="text-[11px] font-semibold">{s.t}</b>
                      <span className="font-mono text-[10px] text-muted-foreground">{s.dur} 秒</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ── 右：tabs · 元数据 + 评论 ─ */}
        <div className="grid gap-4">
          <Card>
            <CardContent className="p-4">
              <Tabs defaultValue="meta">
                <TabsList className="w-full">
                  <TabsTrigger value="meta" className="flex-1">概况</TabsTrigger>
                  <TabsTrigger value="comments" className="flex-1">评论 ({COMMENTS.length})</TabsTrigger>
                  <TabsTrigger value="versions" className="flex-1">版本 (17)</TabsTrigger>
                </TabsList>

                <TabsContent value="meta" className="mt-4 grid gap-2 text-sm">
                  {[
                    ["状态", <StatusBadge key="s" status="rendering" />],
                    ["简报", "春季智能腕环新品上市"],
                    ["模板", "发布主推 v3.1"],
                    ["品牌套件", "Acme · 核心版 v3"],
                    ["画幅", "9:16 · 1080×1920 · 60 fps · H.264 high"],
                    ["时长", "28.0 秒 · 6 个场景"],
                    ["配音", "灵韵 · 女声 · -14 LUFS"],
                    ["负责人", "Ava Chen"],
                    ["审核员", "Priya Rao · Diego Alvarez"],
                  ].map(([k, v]) => (
                    <div key={k as string} className="grid grid-cols-[100px_1fr] gap-3 py-1.5">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd className="text-foreground">{v}</dd>
                    </div>
                  ))}
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
                    <div key={c.cite} className="grid gap-1.5 rounded-md border border-border bg-card/40 p-3 text-sm">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-5 w-5 text-[9px]">
                          <AvatarFallback>{c.who.slice(0, 2)}</AvatarFallback>
                        </Avatar>
                        <b className="font-semibold">{c.who}</b>
                        <time className="ml-auto font-mono text-[10px] text-muted-foreground">{c.when}</time>
                      </div>
                      <div className="text-muted-foreground">{c.text}</div>
                      <div className="font-mono text-[10px] text-accent-300">{c.cite}</div>
                    </div>
                  ))}
                  <Textarea rows={3} placeholder="回复，或 @ 提及制作人…" />
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm">保存草稿</Button>
                    <Button size="sm">
                      <MessageSquare className="h-3.5 w-3.5" /> 发送
                    </Button>
                  </div>
                </TabsContent>

                <TabsContent value="versions" className="mt-4 grid gap-2">
                  {[
                    { v: "v17", title: "加急渲染 · Priya 的 CTA 文案", who: "Ava Chen · 4 分钟前", current: true },
                    { v: "v16", title: "音乐压低到 -6 dB", who: "Diego Alvarez · 28 分钟前" },
                    { v: "v15", title: "片尾卡片替换", who: "Marcus Lee · 1 小时前" },
                    { v: "v14", title: "Diego 批准", who: "Diego Alvarez · 4 小时前" },
                  ].map((r) => (
                    <div
                      key={r.v}
                      className="grid grid-cols-[60px_1fr_auto] items-center gap-3 rounded-md border border-border bg-card/50 p-3"
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
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  );
}
