"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Sparkles,
  Loader2,
  AlertTriangle,
  Music2,
  Mic,
  Film,
  Wand2,
  Captions,
  Cpu,
  Download,
  CheckCircle2,
  Circle,
  XCircle,
  Hash,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  api,
  type GenerateVideoResponse,
  type GenerateVideoSteps,
  type ScriptResponse,
  type StockStatus,
} from "@/lib/api";

// 与后端 storage/samples/* 对齐，默认用打包好的演示素材。
const DEFAULT_CLIPS = [
  "storage/samples/clip_a.mp4",
  "storage/samples/clip_b.mp4",
  "storage/samples/clip_c.mp4",
];
const DEFAULT_BGM = "storage/samples/bgm.wav";
const DEFAULT_LOGO = "storage/samples/logo.png";

const VOICES = [
  { alias: "xiaoxiao-zh-f", label: "晓晓 · 女声 · 亲切" },
  { alias: "yunyang-zh-m", label: "云扬 · 男声 · 沉稳" },
  { alias: "xiaoyi-zh-f", label: "晓伊 · 女声 · 明亮" },
  { alias: "yunxia-zh-m", label: "云夏 · 男声 · 年轻" },
  { alias: "xiaoxuan-zh-f", label: "晓萱 · 女声 · 知性" },
];

const LOOKS = [
  { key: "natural", label: "自然" },
  { key: "warm", label: "暖调" },
  { key: "cool", label: "冷调" },
  { key: "cinematic", label: "电影感" },
  { key: "punchy", label: "高对比" },
];

const PRESETS = [
  { key: "preview_360_9x16", label: "竖屏预览 (快)" },
  { key: "social_9x16", label: "竖屏高清 9:16" },
  { key: "hero_16x9", label: "横屏 16:9" },
  { key: "square_1x1", label: "方形 1:1" },
];

const STEP_ORDER: (keyof GenerateVideoSteps)[] = ["stock", "script", "tts", "asr", "mix", "cover"];
const STEP_LABEL: Record<string, string> = {
  stock: "拉素材",
  script: "脚本生成",
  tts: "配音 (edge-tts)",
  asr: "字幕识别",
  mix: "智能混剪",
  cover: "封面",
};

const EXAMPLE_TOPICS = [
  "春季美容补水套餐 — 新客首单 5 折",
  "七夕款美甲新色上新",
  "肩颈舒缓 SPA 90 分钟招牌套餐",
  "私教减脂 12 周训练营开启",
  "周末精品咖啡 - 新豆上线",
  "新店开业 — 全场 7 折前三天",
];

type StockMode = "sample" | "pexels" | "url";

export function StudioGenerate() {
  const [topic, setTopic] = useState(EXAMPLE_TOPICS[0]);
  const [voice, setVoice] = useState(VOICES[0].alias);
  const [look, setLook] = useState("cinematic");
  const [preset, setPreset] = useState("preview_360_9x16");
  const [length, setLength] = useState(200);
  const [skipAsr, setSkipAsr] = useState(true);
  const [adaptiveMix, setAdaptiveMix] = useState(true);
  const [autoWB, setAutoWB] = useState(true);
  const [clipPaths, setClipPaths] = useState<string[]>(DEFAULT_CLIPS);
  const [bgmPath, setBgmPath] = useState(DEFAULT_BGM);
  const [logoPath, setLogoPath] = useState(DEFAULT_LOGO);
  const [stockMode, setStockMode] = useState<StockMode>("sample");
  const [pexelsQuery, setPexelsQuery] = useState("");
  const [pexelsCount, setPexelsCount] = useState(3);
  const [urlInput, setUrlInput] = useState("");
  const [urlSection, setUrlSection] = useState("*0:00-0:08");
  const [stockStatus, setStockStatus] = useState<StockStatus | null>(null);
  const [stockLoading, setStockLoading] = useState(false);

  const [script, setScript] = useState<ScriptResponse | null>(null);
  const [scriptLoading, setScriptLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [job, setJob] = useState<GenerateVideoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pollHandle = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (pollHandle.current) clearInterval(pollHandle.current);
    };
  }, []);

  useEffect(() => {
    let alive = true;
    api.stockStatus().then((s) => {
      if (alive) setStockStatus(s);
    });
    return () => {
      alive = false;
    };
  }, []);

  async function pullFromUrl() {
    if (!urlInput.trim()) return;
    setStockLoading(true);
    setError(null);
    try {
      const result = await api.stockFromUrl({
        url: urlInput.trim(),
        sections: urlSection || undefined,
        max_height: 1080,
      });
      setClipPaths([result.path, ...clipPaths].slice(0, 5));
      setUrlInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStockLoading(false);
    }
  }

  async function previewScript() {
    setScriptLoading(true);
    setError(null);
    try {
      const result = await api.generateScript({ topic, length });
      setScript(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setScriptLoading(false);
    }
  }

  async function startGenerate() {
    setGenerating(true);
    setJob(null);
    setError(null);
    try {
      const initial = await api.generateVideo({
        topic,
        clip_paths: stockMode === "pexels" ? [] : clipPaths.filter(Boolean),
        voice,
        bgm_path: bgmPath || undefined,
        watermark_path: logoPath || undefined,
        title: topic.split(/[—\-]/)[0].trim(),
        preset,
        color_look: look === "natural" ? undefined : look,
        skip_asr: skipAsr,
        adaptive_bgm_mix: adaptiveMix,
        auto_white_balance: autoWB,
        length,
        stock_source: stockMode === "pexels" ? "pexels" : "manual",
        stock_query: stockMode === "pexels" ? (pexelsQuery || topic) : undefined,
        stock_count: pexelsCount,
        stock_orientation: preset.endsWith("16x9") ? "landscape" : "portrait",
      });
      setJob(initial);
      if (pollHandle.current) clearInterval(pollHandle.current);
      pollHandle.current = window.setInterval(async () => {
        try {
          const status = await api.generateVideoStatus(initial.job_id);
          setJob(status);
          if (status.status === "succeeded" || status.status === "failed") {
            if (pollHandle.current) clearInterval(pollHandle.current);
            pollHandle.current = null;
            setGenerating(false);
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err));
          if (pollHandle.current) clearInterval(pollHandle.current);
          pollHandle.current = null;
          setGenerating(false);
        }
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setGenerating(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_440px]">
      {/* 左：商家信息 + 配置 */}
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Wand2 className="text-accent-300" size={18} />
            商家信息
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5">
          <div className="grid gap-2">
            <Label htmlFor="topic">主题</Label>
            <Input
              id="topic"
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value);
                setScript(null);
              }}
              placeholder="例：春季美容补水套餐 - 新客首单 5 折"
            />
            <div className="flex flex-wrap gap-1.5">
              {EXAMPLE_TOPICS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => {
                    setTopic(t);
                    setScript(null);
                  }}
                  className="rounded-full border border-white/10 bg-white/[0.02] px-2.5 py-1 text-[11px] text-muted-foreground hover:border-white/20 hover:text-foreground"
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-2 rounded-md border border-white/10 bg-white/[0.02] p-3">
            <Label className="text-xs text-muted-foreground">视频素材来源</Label>
            <div className="grid grid-cols-3 gap-1.5">
              <SourceChip
                active={stockMode === "sample"}
                onClick={() => setStockMode("sample")}
                label="内置示例"
                hint="3 个测试素材"
              />
              <SourceChip
                active={stockMode === "pexels"}
                onClick={() => setStockMode("pexels")}
                label="Pexels"
                hint={stockStatus?.pexels.configured ? "已配置 key" : "需要 API key"}
                warn={!stockStatus?.pexels.configured}
              />
              <SourceChip
                active={stockMode === "url"}
                onClick={() => setStockMode("url")}
                label="自定义 URL"
                hint="yt-dlp"
                warn={!stockStatus?.ytdlp.configured}
              />
            </div>

            {stockMode === "pexels" && (
              <div className="grid gap-2 pt-2">
                <Input
                  value={pexelsQuery}
                  onChange={(e) => setPexelsQuery(e.target.value)}
                  placeholder={`关键词（留空则用主题）— 例: skincare, nail salon`}
                />
                <div className="flex items-center gap-2">
                  <Label className="text-xs text-muted-foreground">数量</Label>
                  <input
                    type="range"
                    min={1}
                    max={6}
                    value={pexelsCount}
                    onChange={(e) => setPexelsCount(Number(e.target.value))}
                    className="flex-1 accent-accent-500"
                  />
                  <span className="text-xs text-muted-foreground w-6 text-right">{pexelsCount}</span>
                </div>
                {!stockStatus?.pexels.configured && (
                  <p className="text-[11px] text-amber-200/90">
                    需要先在终端 <code className="rounded bg-white/10 px-1">export PEXELS_API_KEY=xxx</code>{" "}
                    再重启后端 · 注册 <a href="https://www.pexels.com/api/" target="_blank" rel="noreferrer" className="underline">pexels.com/api</a>
                  </p>
                )}
              </div>
            )}

            {stockMode === "url" && (
              <div className="grid gap-2 pt-2">
                <Input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="粘贴视频 URL（YouTube / B站 / 抖音 / 任意 yt-dlp 支持的站点）"
                />
                <div className="flex gap-2">
                  <Input
                    value={urlSection}
                    onChange={(e) => setUrlSection(e.target.value)}
                    placeholder="时间段，例 *0:00-0:08"
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={pullFromUrl}
                    disabled={stockLoading || !urlInput.trim()}
                  >
                    {stockLoading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                    拉取
                  </Button>
                </div>
                {clipPaths.filter((p) => p && !p.startsWith("storage/samples/")).length > 0 && (
                  <div className="text-[11px] text-muted-foreground">
                    已拉取 {clipPaths.filter((p) => p && !p.startsWith("storage/samples/")).length} 个素材
                  </div>
                )}
              </div>
            )}

            {stockMode === "sample" && (
              <p className="text-[11px] text-muted-foreground pt-1">
                内置 ffmpeg 生成的测试素材（彩条/纯色）。换成 Pexels 或 URL 能拿到真实画面。
              </p>
            )}
          </div>

          <div className="grid gap-2">
            <div className="flex items-center justify-between">
              <Label>脚本预览（可选）</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={previewScript}
                disabled={scriptLoading}
              >
                {scriptLoading ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                生成脚本
              </Button>
            </div>
            {script ? (
              <div className="grid gap-2 rounded-md border border-white/10 bg-white/[0.02] p-3 text-xs">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-accent-500/15 text-accent-200">
                    {script.scenario}
                  </Badge>
                  <span className="text-muted-foreground">
                    ≈ {script.estimated_seconds.toFixed(1)}s · {script.content.length} 字
                  </span>
                </div>
                <p className="whitespace-pre-line text-foreground/90">{script.content}</p>
                <p className="text-accent-300 flex items-center gap-1">
                  <Hash size={11} />
                  {script.keywords}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                可选：先看一眼脚本草稿。后面「立即生成」时会自动重跑。
              </p>
            )}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="voice">配音音色</Label>
              <select
                id="voice"
                value={voice}
                onChange={(e) => setVoice(e.target.value)}
                className="h-9 rounded-md border border-border bg-card/50 px-3 text-sm focus:border-accent-500/40 focus:outline-none"
              >
                {VOICES.map((v) => (
                  <option key={v.alias} value={v.alias}>
                    {v.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="preset">输出格式</Label>
              <select
                id="preset"
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
                className="h-9 rounded-md border border-border bg-card/50 px-3 text-sm focus:border-accent-500/40 focus:outline-none"
              >
                {PRESETS.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label className="text-xs text-muted-foreground">调色 LUT</Label>
            <div className="flex flex-wrap gap-1.5">
              {LOOKS.map((l) => (
                <button
                  key={l.key}
                  type="button"
                  onClick={() => setLook(l.key)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors",
                    look === l.key
                      ? "border-accent-500/60 bg-accent-500/15 text-accent-200"
                      : "border-white/10 bg-white/[0.02] text-muted-foreground hover:border-white/20 hover:text-foreground",
                  )}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="length" className="flex items-center justify-between">
              <span>脚本目标字数</span>
              <span className="text-muted-foreground">{length} 字 · ≈ {(length / 5).toFixed(1)}s</span>
            </Label>
            <input
              id="length"
              type="range"
              min={80}
              max={400}
              step={10}
              value={length}
              onChange={(e) => setLength(Number(e.target.value))}
              className="accent-accent-500"
            />
          </div>

          <details className="grid gap-2 rounded-md border border-white/5 bg-white/[0.02] p-3 text-xs">
            <summary className="cursor-pointer text-muted-foreground">高级 · 素材路径 + 开关</summary>
            <div className="mt-3 grid gap-2.5">
              {clipPaths.map((p, i) => (
                <Input
                  key={i}
                  value={p}
                  onChange={(e) => {
                    const next = [...clipPaths];
                    next[i] = e.target.value;
                    setClipPaths(next);
                  }}
                  placeholder={`素材 ${i + 1}`}
                />
              ))}
              <Input
                value={bgmPath}
                onChange={(e) => setBgmPath(e.target.value)}
                placeholder="BGM 路径（可空）"
              />
              <Input
                value={logoPath}
                onChange={(e) => setLogoPath(e.target.value)}
                placeholder="水印 PNG 路径（可空）"
              />
              <Toggle
                label="跳过 Whisper 字幕识别"
                hint="勾选时用脚本切分；不勾选会跑 faster-whisper（首次下载模型 ~74MB）"
                checked={skipAsr}
                onChange={setSkipAsr}
              />
              <Toggle
                label="自适应 BGM 混音"
                checked={adaptiveMix}
                onChange={setAdaptiveMix}
              />
              <Toggle
                label="自动白平衡"
                checked={autoWB}
                onChange={setAutoWB}
              />
            </div>
          </details>

          <div className="flex items-center gap-3 pt-1">
            <Button size="lg" onClick={startGenerate} disabled={generating || !topic.trim()}>
              {generating ? (
                <>
                  <Loader2 className="animate-spin" /> 生产中…
                </>
              ) : (
                <>
                  <Wand2 /> 立即生成视频
                </>
              )}
            </Button>
            <p className="text-xs text-muted-foreground">
              全流程约 10–20 秒（视素材数量与是否 ASR）
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span className="whitespace-pre-wrap break-all">{error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 右：流水线进度 + 结果 */}
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles size={18} className="text-accent-300" /> 流水线
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <StepList steps={job?.steps ?? defaultSteps()} />

          {!job?.output ? (
            <div className="flex aspect-[9/16] flex-col items-center justify-center gap-2 rounded-md border border-dashed border-white/10 bg-white/[0.02] p-6 text-center">
              {generating ? (
                <>
                  <Loader2 className="animate-spin text-accent-300" size={24} />
                  <p className="text-sm text-muted-foreground">脚本 → 配音 → 字幕 → 混剪 → 封面…</p>
                </>
              ) : (
                <>
                  <Mic size={24} className="text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    输入主题，点 <span className="font-semibold text-foreground">「立即生成视频」</span>
                  </p>
                </>
              )}
            </div>
          ) : (
            <Output job={job} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function defaultSteps(): GenerateVideoSteps {
  return {
    stock: "skipped",
    script: "pending",
    tts: "pending",
    asr: "pending",
    mix: "pending",
    cover: "pending",
  };
}

function StepList({ steps }: { steps: GenerateVideoSteps }) {
  return (
    <ol className="grid gap-1.5 rounded-md border border-white/5 bg-white/[0.02] p-3 text-xs">
      {STEP_ORDER.map((k) => {
        const s = ((steps as Record<string, string>)[k] || "pending") as string;
        return (
          <li key={k} className="flex items-center gap-2">
            <StepIcon status={s} />
            <span className="flex-1 text-foreground/90">{STEP_LABEL[k]}</span>
            <span className={cn("text-[10px] uppercase tracking-wide", statusColor(s))}>
              {statusLabel(s)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function StepIcon({ status }: { status: string }) {
  if (status === "succeeded") return <CheckCircle2 size={14} className="text-emerald-400" />;
  if (status === "running") return <Loader2 size={14} className="animate-spin text-accent-300" />;
  if (status === "skipped") return <Circle size={14} className="text-muted-foreground/60" />;
  if (status.startsWith("failed")) return <XCircle size={14} className="text-destructive" />;
  return <Circle size={14} className="text-muted-foreground/60" />;
}

function statusColor(status: string) {
  if (status === "succeeded") return "text-emerald-400";
  if (status === "running") return "text-accent-300";
  if (status === "skipped") return "text-muted-foreground";
  if (status.startsWith("failed")) return "text-destructive";
  return "text-muted-foreground";
}

function statusLabel(status: string) {
  if (status === "succeeded") return "OK";
  if (status === "running") return "进行中";
  if (status === "skipped") return "跳过";
  if (status.startsWith("failed")) return "失败";
  return "等待";
}

function Output({ job }: { job: GenerateVideoResponse }) {
  const o = job.output!;
  return (
    <>
      <video
        className="w-full rounded-md border border-white/10 bg-black"
        src={o.video_url}
        poster={o.cover_url ?? undefined}
        controls
        playsInline
      />

      <details open className="rounded-md border border-white/5 bg-white/[0.02] p-3 text-xs">
        <summary className="cursor-pointer text-muted-foreground">脚本 · {o.scenario}</summary>
        <p className="mt-2 whitespace-pre-line text-foreground/90">{o.script}</p>
        <p className="mt-2 text-accent-300 flex items-center gap-1">
          <Hash size={11} />
          {o.keywords}
        </p>
      </details>

      <dl className="grid grid-cols-2 gap-3 text-xs">
        <Stat label="时长" value={`${o.duration.toFixed(2)}s`} />
        <Stat label="过渡" value={o.transitions.join(" · ") || "—"} />
      </dl>

      <a
        className="inline-flex items-center gap-2 self-start text-xs text-accent-300 hover:underline"
        href={o.video_url}
        download
      >
        <Download size={12} /> 下载 MP4
      </a>

      {o.warnings.length > 0 && (
        <details className="rounded-md border border-white/5 bg-white/[0.02] p-3 text-xs">
          <summary className="cursor-pointer text-muted-foreground">
            管线说明 · {o.warnings.length} 条
          </summary>
          <ul className="mt-2 grid gap-1 pl-4 text-muted-foreground/90">
            {o.warnings.map((w, i) => (
              <li key={i} className="list-disc">
                {w}
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.03] p-2.5">
      <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="font-display text-sm font-medium">{value}</dd>
    </div>
  );
}

function SourceChip({
  active,
  onClick,
  label,
  hint,
  warn,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  hint: string;
  warn?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "grid gap-0.5 rounded-md border px-3 py-2 text-left transition-colors",
        active
          ? "border-accent-500/60 bg-accent-500/10"
          : "border-white/10 bg-white/[0.02] hover:border-white/20",
      )}
    >
      <span className={cn("text-xs font-semibold", active ? "text-accent-200" : "text-foreground")}>
        {label}
      </span>
      <span className={cn("text-[10px]", warn && !active ? "text-amber-300/80" : "text-muted-foreground")}>
        {hint}
      </span>
    </button>
  );
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-md border border-white/5 bg-white/[0.02] px-3 py-2 hover:border-white/10">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-4 accent-accent-500"
      />
      <span className="flex flex-1 flex-col">
        <span className="text-sm">{label}</span>
        {hint && <span className="text-[11px] text-muted-foreground">{hint}</span>}
      </span>
    </label>
  );
}
