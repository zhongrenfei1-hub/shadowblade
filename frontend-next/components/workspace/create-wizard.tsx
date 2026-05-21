"use client";

import { useEffect, useState } from "react";
import {
  Sparkles,
  Upload,
  Folder,
  Mic,
  Captions,
  Film,
  Droplet,
  Loader2,
  Check,
  ChevronRight,
  Zap,
  Image as ImageIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

const TEMPLATES = [
  { slug: "hero-launch", name: "发布主推", desc: "9:16 · 30 秒 · 营销", recommended: true },
  { slug: "product-explainer", name: "产品讲解", desc: "16:9 · 60 秒 · 演示" },
  { slug: "training-module", name: "培训模块", desc: "16:9 · 3 分钟 · 培训" },
  { slug: "social-teaser", name: "社交预告", desc: "9:16 · 15 秒 · 社交" },
];

const VOICES = [
  { id: "alloy-zh-f", name: "灵韵 · 女声", tone: "自信、平实" },
  { id: "ember-zh-m", name: "炽炎 · 男声", tone: "温暖、稳重" },
  { id: "lumen-zh-f", name: "晨曦 · 女声", tone: "明亮、活泼" },
];

/**
 * 标准 6 步流水线 · 对齐 Hero 文案：
 * 脚本 → 语音 → 字幕 → 混剪 → 封面 → 品牌水印
 */
const PIPELINE = [
  { key: "script", label: "脚本", icon: Sparkles },
  { key: "voice", label: "语音", icon: Mic },
  { key: "captions", label: "字幕", icon: Captions },
  { key: "mix", label: "混剪", icon: Film },
  { key: "cover", label: "封面", icon: ImageIcon },
  { key: "watermark", label: "品牌水印", icon: Droplet },
];

export function CreateWizard() {
  const [template, setTemplate] = useState("hero-launch");
  const [purpose, setPurpose] = useState<"marketing" | "training" | "product_demo" | "social">("marketing");
  const [aspect, setAspect] = useState("9:16");
  const [duration, setDuration] = useState("30");
  const [voice, setVoice] = useState("alloy-zh-f");
  const [brief, setBrief] = useState(
    "春季智能腕环新品上市。卖点：7 天续航、12 项健康指标、单手轻触。受众：28–42 岁的运动型职场人，覆盖中国一二线城市。语态：自信、平实、不夸张。CTA：现在预定，首批 1000 台免运费。"
  );
  const [cta, setCta] = useState("现在预定，首批 1000 台免运费");
  const [running, setRunning] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => {
      setStep((s) => {
        const next = s + 1;
        if (next >= PIPELINE.length) {
          setRunning(false);
          return PIPELINE.length;
        }
        return next;
      });
    }, 800);
    return () => clearInterval(t);
  }, [running]);

  function start() {
    setStep(0);
    setRunning(true);
  }

  return (
    <section className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr] items-start">
      {/* ── 左：表单 ─────────────────────── */}
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>1. 选模板</CardTitle>
            <p className="text-sm text-muted-foreground">挑一个最接近你目标的开头，后面所有参数可微调。</p>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {TEMPLATES.map((t) => (
              <button
                key={t.slug}
                type="button"
                onClick={() => setTemplate(t.slug)}
                className={cn(
                  "relative flex flex-col gap-3 rounded-md border border-border bg-card/40 p-4 text-left transition-all",
                  "hover:-translate-y-0.5 hover:border-accent-500/40",
                  template === t.slug && "border-accent-500 bg-accent-500/[0.06]"
                )}
              >
                <div className="h-[60px] rounded bg-gradient-to-br from-navy-700 to-navy-900" />
                <div className="flex items-center gap-2">
                  <b className="font-display text-sm">{t.name}</b>
                  {t.recommended && (
                    <Badge variant="default" className="text-[9px]">推荐</Badge>
                  )}
                </div>
                <span className="text-xs text-muted-foreground">{t.desc}</span>
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>2. 填写视频需求</CardTitle>
            <p className="text-sm text-muted-foreground">越清楚的简报，越对得起品牌的成片。</p>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Tabs value={purpose} onValueChange={(v) => setPurpose(v as typeof purpose)}>
              <TabsList className="w-full">
                <TabsTrigger value="marketing" className="flex-1">营销</TabsTrigger>
                <TabsTrigger value="product_demo" className="flex-1">产品演示</TabsTrigger>
                <TabsTrigger value="training" className="flex-1">培训</TabsTrigger>
                <TabsTrigger value="social" className="flex-1">社交推广</TabsTrigger>
              </TabsList>
              <TabsContent value="marketing" className="sr-only">已选：营销视频</TabsContent>
              <TabsContent value="product_demo" className="sr-only">已选：产品演示</TabsContent>
              <TabsContent value="training" className="sr-only">已选：培训视频</TabsContent>
              <TabsContent value="social" className="sr-only">已选：社交推广</TabsContent>
            </Tabs>

            <div className="grid gap-1.5">
              <Label htmlFor="brief">简报</Label>
              <Textarea
                id="brief"
                rows={5}
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder="一段话写清楚：是给谁看的、说什么卖点、什么语态、最后让用户做什么。"
              />
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="grid gap-1.5">
                <Label htmlFor="aspect">画幅</Label>
                <select
                  id="aspect"
                  value={aspect}
                  onChange={(e) => setAspect(e.target.value)}
                  className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="9:16">9:16 竖屏</option>
                  <option value="16:9">16:9 横屏</option>
                  <option value="1:1">1:1 方形</option>
                </select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="duration">时长</Label>
                <select
                  id="duration"
                  value={duration}
                  onChange={(e) => setDuration(e.target.value)}
                  className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="15">15 秒</option>
                  <option value="30">30 秒</option>
                  <option value="60">60 秒</option>
                  <option value="90">90 秒</option>
                </select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="voice">配音</Label>
                <select
                  id="voice"
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {VOICES.map((v) => (
                    <option key={v.id} value={v.id}>{v.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="cta">行动号召</Label>
              <Input
                id="cta"
                value={cta}
                onChange={(e) => setCta(e.target.value)}
                placeholder="一句话告诉观众下一步做什么。"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>3. 选素材（可选）</CardTitle>
            <p className="text-sm text-muted-foreground">不上传也行 — AI 会从你的素材库 + 授权图库匹配。</p>
          </CardHeader>
          <CardContent className="grid gap-3">
            <button
              type="button"
              aria-label="上传素材文件"
              className="grid place-items-center gap-3 rounded-lg border-[1.5px] border-dashed border-accent-500/40 bg-accent-500/[0.05] p-6 text-center transition-colors hover:bg-accent-500/[0.08]"
            >
              <Upload className="h-7 w-7 text-accent-300" aria-hidden />
              <b className="font-display text-sm">拖入文件，或点击上传</b>
              <span className="text-xs text-muted-foreground">MP4 / MOV / PNG / JPG / MP3 · 单个最大 4 GB</span>
            </button>
            <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <Button variant="outline" className="justify-start">
                <Folder className="h-4 w-4" /> 从素材库选
              </Button>
              <Button variant="outline" className="justify-start">
                <Sparkles className="h-4 w-4" /> AI 自动匹配
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── 右：一键生成 + 进度 ─────────── */}
      <div className="sticky top-[76px] grid gap-4">
        <Card className="border-accent-500/50 bg-gradient-to-b from-accent-500/[0.08] to-card/85">
          <CardHeader>
            <CardTitle>4. 一键生成</CardTitle>
            <p className="text-sm text-muted-foreground">流水线并行 6 步。首版预计 <b className="text-foreground num">4 分 32 秒</b>。</p>
          </CardHeader>
          <CardContent className="grid gap-4">
            <Button
              size="xl"
              onClick={start}
              disabled={running}
              className="w-full text-base shadow-[0_24px_48px_-16px_rgba(34,211,183,0.7)]"
            >
              {running ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  正在生成（{step}/6）
                </>
              ) : (
                <>
                  <Zap className="h-5 w-5 fill-current" />
                  一键生成视频
                </>
              )}
            </Button>

            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              <span>预计时长</span>
              <span className="text-right font-mono text-foreground">{duration} 秒 · {aspect}</span>
              <span>当前队列</span>
              <span className="text-right font-mono text-foreground">3 个加急 · 1 个常规</span>
              <span>预计费用</span>
              <span className="text-right font-mono text-foreground">$1.40</span>
              <span>渲染后</span>
              <span className="text-right font-mono text-foreground">立即可下载 / 分享</span>
            </div>

            <div className="rounded-md border border-border bg-card/60 p-3">
              <div className="mb-3 flex items-center justify-between text-xs">
                <span className="font-semibold uppercase tracking-wider text-muted-foreground">流水线进度</span>
                {running && (
                  <span className="font-mono text-accent-300">
                    {Math.round((step / PIPELINE.length) * 100)}%
                  </span>
                )}
              </div>
              <Progress value={(step / PIPELINE.length) * 100} className="mb-3" />
              <ul className="grid gap-2">
                {PIPELINE.map((p, i) => {
                  const Icon = p.icon;
                  const done = step > i;
                  const active = running && step === i;
                  return (
                    <li
                      key={p.key}
                      className={cn(
                        "flex items-center gap-2 text-xs transition-colors",
                        done ? "text-accent-300" : active ? "text-foreground" : "text-muted-foreground"
                      )}
                    >
                      {done ? (
                        <Check className="h-3.5 w-3.5" />
                      ) : active ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Icon className="h-3.5 w-3.5" />
                      )}
                      <span>{p.label}</span>
                      {active && <span className="ml-auto font-mono text-[10px]">运行中</span>}
                      {done && <span className="ml-auto font-mono text-[10px]">完成</span>}
                    </li>
                  );
                })}
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">智能建议</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-xs text-muted-foreground">
            <div className="flex items-start gap-2">
              <span className="grid h-5 w-5 place-items-center rounded bg-sky-500/15 text-sky-300">★</span>
              <span>加一段 CTA 收尾 — 同模板上轮转化高 22%</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="grid h-5 w-5 place-items-center rounded bg-violet-500/15 text-violet-300">✿</span>
              <span>从「创始人空镜」库匹配 2 段镜头 · 已审核 · CC 协议</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="grid h-5 w-5 place-items-center rounded bg-accent-500/15 text-accent-300">↻</span>
              <span>同时翻译成英文 / 日文 · 多语种版本会加约 2 分钟</span>
            </div>
            <Button variant="link" size="sm" className="ml-auto h-auto p-0">
              查看全部建议 <ChevronRight className="h-3 w-3" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
