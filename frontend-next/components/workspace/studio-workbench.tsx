"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Sparkles,
  Loader2,
  AlertTriangle,
  Music2,
  Mic,
  Film,
  Palette,
  Captions,
  Cpu,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  api,
  type MixCue,
  type MixFeatures,
  type MixSubtitleIssue,
  type MixVideoResponse,
} from "@/lib/api";

// 后端在第一轮就生成了 storage/samples/* —— 提供默认值，用户首次进来就能一键跑通。
const DEFAULT_SAMPLES = {
  clipA: "/Users/qiu/工作流/shadowblade/storage/samples/clip_a.mp4",
  clipB: "/Users/qiu/工作流/shadowblade/storage/samples/clip_b.mp4",
  clipC: "/Users/qiu/工作流/shadowblade/storage/samples/clip_c.mp4",
  voice: "/Users/qiu/工作流/shadowblade/storage/samples/voice.wav",
  bgm: "/Users/qiu/工作流/shadowblade/storage/samples/bgm.wav",
  logo: "/Users/qiu/工作流/shadowblade/storage/samples/logo.png",
};

const LOOKS = [
  { key: "natural", label: "自然" },
  { key: "warm", label: "暖调" },
  { key: "cool", label: "冷调" },
  { key: "cinematic", label: "电影感" },
  { key: "punchy", label: "高对比" },
  { key: "mono", label: "黑白" },
  { key: "vintage", label: "复古" },
] as const;

const ASPECTS = [
  { key: "social_9x16", label: "竖屏 9:16" },
  { key: "hero_16x9", label: "横屏 16:9" },
  { key: "square_1x1", label: "方形 1:1" },
] as const;

const TRANSITIONS = [
  { key: "editorial", label: "编辑级" },
  { key: "energetic", label: "高能" },
  { key: "calm", label: "克制" },
] as const;

const DEFAULT_CUES: MixCue[] = [
  { start: 0.3, end: 2.4, text: "新一代智能腕环来了" },
  { start: 2.8, end: 5.0, text: "续航三十天，全场景健康监测" },
  { start: 5.4, end: 7.4, text: "今天开售" },
];

function cuesToScript(cues: MixCue[]): string {
  return cues.map((c) => `${c.start.toFixed(1)}-${c.end.toFixed(1)} ${c.text}`).join("\n");
}

function scriptToCues(text: string): MixCue[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const m = line.match(/^(\d+(?:\.\d+)?)[-–~](\d+(?:\.\d+)?)\s+(.*)$/);
      if (!m) return null;
      return { start: parseFloat(m[1]), end: parseFloat(m[2]), text: m[3] } as MixCue;
    })
    .filter((c): c is MixCue => c !== null);
}

function toBrowserUrl(absOrRel: string): string {
  if (!absOrRel) return "";
  const cleaned = absOrRel.replace(/^\.?\/+/, "");
  if (cleaned.startsWith("storage/")) return `/static/${cleaned}`;
  if (cleaned.startsWith("/static/")) return cleaned;
  const idx = absOrRel.indexOf("/storage/");
  if (idx >= 0) return `/static${absOrRel.slice(idx)}`;
  return absOrRel;
}

export function StudioWorkbench() {
  const [features, setFeatures] = useState<MixFeatures | null>(null);
  const [voicePath, setVoicePath] = useState(DEFAULT_SAMPLES.voice);
  const [bgmPath, setBgmPath] = useState(DEFAULT_SAMPLES.bgm);
  const [logoPath, setLogoPath] = useState(DEFAULT_SAMPLES.logo);
  const [title, setTitle] = useState("新一代智能腕环");
  const [look, setLook] = useState<string>("cinematic");
  const [aspect, setAspect] = useState<string>("social_9x16");
  const [transitionStyle, setTransitionStyle] = useState<string>("editorial");
  const [snapBeats, setSnapBeats] = useState(false);
  const [autoWB, setAutoWB] = useState(true);
  const [adaptiveMix, setAdaptiveMix] = useState(true);
  const [scriptText, setScriptText] = useState(cuesToScript(DEFAULT_CUES));
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<MixVideoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    api.mixFeatures().then((f) => {
      if (alive) setFeatures(f);
    });
    return () => {
      alive = false;
    };
  }, []);

  const cues = useMemo(() => scriptToCues(scriptText), [scriptText]);

  async function handleGenerate() {
    setRunning(true);
    setError(null);
    setResult(null);
    const projectId = `studio-${Date.now().toString(36)}`;
    try {
      const res = await api.mixPreview({
        project_id: projectId,
        clips: [
          { path: DEFAULT_SAMPLES.clipA, end: 3.0, is_hero: true },
          { path: DEFAULT_SAMPLES.clipB, end: 2.5 },
          { path: DEFAULT_SAMPLES.clipC, end: 2.0, is_chapter_break: true },
        ],
        voice_path: voicePath || undefined,
        bgm_path: bgmPath || undefined,
        watermark_path: logoPath || undefined,
        watermark_position: "br",
        cues,
        title,
        preset: aspect,
        color_look: look === "natural" ? undefined : look,
        auto_white_balance: autoWB,
        transition_style: transitionStyle as "editorial" | "energetic" | "calm",
        snap_to_beats: snapBeats,
        adaptive_bgm_mix: adaptiveMix,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  const videoUrl = result ? toBrowserUrl(result.output_path) : "";
  const coverUrl = result?.cover_path ? toBrowserUrl(result.cover_path) : "";

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px]">
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="text-accent-300" size={18} />
            混剪参数
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-5">
          <FeaturesBadgeRow features={features} />

          <div className="grid gap-2">
            <Label htmlFor="title">标题（覆盖到封面）</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="例：新一代智能腕环"
            />
          </div>

          <Tabs defaultValue="look" className="w-full">
            <TabsList className="w-full justify-start gap-1 overflow-x-auto">
              <TabsTrigger value="look">
                <Palette size={14} /> 调色
              </TabsTrigger>
              <TabsTrigger value="aspect">
                <Film size={14} /> 比例
              </TabsTrigger>
              <TabsTrigger value="transitions">
                <Sparkles size={14} /> 过渡
              </TabsTrigger>
              <TabsTrigger value="audio">
                <Music2 size={14} /> 音轨
              </TabsTrigger>
              <TabsTrigger value="captions">
                <Captions size={14} /> 字幕
              </TabsTrigger>
            </TabsList>

            <TabsContent value="look" className="grid gap-3 pt-3">
              <ChipGroup
                label="色彩 LUT 预设"
                options={LOOKS}
                value={look}
                onChange={setLook}
              />
              <Toggle
                label="自动白平衡"
                checked={autoWB}
                onChange={setAutoWB}
                hint="对源素材偏色做粗略校正"
              />
            </TabsContent>

            <TabsContent value="aspect" className="grid gap-3 pt-3">
              <ChipGroup
                label="编码 preset"
                options={ASPECTS}
                value={aspect}
                onChange={setAspect}
              />
              <p className="text-xs text-muted-foreground">
                预览模式始终走 360p 快速 preset；上方选择决定最终成品比例。
              </p>
            </TabsContent>

            <TabsContent value="transitions" className="grid gap-3 pt-3">
              <ChipGroup
                label="风格"
                options={TRANSITIONS}
                value={transitionStyle}
                onChange={setTransitionStyle}
              />
              <Toggle
                label="切点 snap 到 BGM 节拍"
                checked={snapBeats}
                onChange={setSnapBeats}
                hint="检测 BPM 后把镜头切点对齐节拍"
              />
            </TabsContent>

            <TabsContent value="audio" className="grid gap-3 pt-3">
              <div className="grid gap-2">
                <Label htmlFor="voice">人声路径</Label>
                <Input id="voice" value={voicePath} onChange={(e) => setVoicePath(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="bgm">背景音乐路径</Label>
                <Input id="bgm" value={bgmPath} onChange={(e) => setBgmPath(e.target.value)} />
              </div>
              <Toggle
                label="自适应 BGM 混音"
                checked={adaptiveMix}
                onChange={setAdaptiveMix}
                hint="测量人声 LUFS 自动调整 ducking 阈值和 BGM 增益"
              />
              <div className="grid gap-2">
                <Label htmlFor="logo">品牌水印 PNG</Label>
                <Input id="logo" value={logoPath} onChange={(e) => setLogoPath(e.target.value)} />
              </div>
            </TabsContent>

            <TabsContent value="captions" className="grid gap-3 pt-3">
              <Label htmlFor="script">字幕脚本（每行：start-end 文本）</Label>
              <Textarea
                id="script"
                rows={6}
                value={scriptText}
                onChange={(e) => setScriptText(e.target.value)}
                className="font-mono text-xs"
              />
              <p className="text-xs text-muted-foreground">
                例：<code>0.3-2.4 新一代智能腕环来了</code>
              </p>
            </TabsContent>
          </Tabs>

          <div className="flex items-center gap-3 pt-2">
            <Button size="lg" onClick={handleGenerate} disabled={running}>
              {running ? (
                <>
                  <Loader2 className="animate-spin" /> 生成中…
                </>
              ) : (
                <>
                  <Sparkles /> 立即渲染
                </>
              )}
            </Button>
            <p className="text-xs text-muted-foreground">
              本地 ffmpeg + VideoToolbox · 360p 预览 5–10 秒
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

      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Film size={18} className="text-accent-300" /> 渲染结果
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          {!result ? (
            <EmptyResult features={features} />
          ) : (
            <ResultPanel result={result} videoUrl={videoUrl} coverUrl={coverUrl} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FeaturesBadgeRow({ features }: { features: MixFeatures | null }) {
  if (!features) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="animate-spin" size={12} />
        检测 ffmpeg 能力…
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-[11px]">
      <Badge
        variant="secondary"
        className={cn(
          "gap-1",
          features.has_videotoolbox ? "bg-accent-500/15 text-accent-200" : "bg-white/5 text-muted-foreground",
        )}
      >
        <Cpu size={11} />
        {features.has_videotoolbox ? "VideoToolbox GPU" : "软件编码"}
      </Badge>
      <Badge
        variant="secondary"
        className={cn(
          "gap-1",
          features.can_burn_subtitles ? "bg-white/5 text-muted-foreground" : "bg-amber-500/15 text-amber-200",
        )}
      >
        <Captions size={11} />
        {features.can_burn_subtitles ? "libass 字幕" : "Pillow PNG 字幕"}
      </Badge>
    </div>
  );
}

function EmptyResult({ features }: { features: MixFeatures | null }) {
  return (
    <div className="flex aspect-[9/16] flex-col items-center justify-center gap-2 rounded-md border border-dashed border-white/10 bg-white/[0.02] p-6 text-center">
      <Mic size={24} className="text-muted-foreground" />
      <p className="text-sm text-muted-foreground">
        填好参数后点 <span className="font-semibold text-foreground">「立即渲染」</span>
      </p>
      <p className="text-[11px] text-muted-foreground/80">
        {features?.has_videotoolbox
          ? "GPU 已就绪 · 360p 预览预计 5–10 秒"
          : "等待后端连接 · 见下方 README 启动 make next"}
      </p>
    </div>
  );
}

function ResultPanel({
  result,
  videoUrl,
  coverUrl,
}: {
  result: MixVideoResponse;
  videoUrl: string;
  coverUrl: string;
}) {
  return (
    <>
      <video
        className="w-full rounded-md border border-white/10 bg-black"
        src={videoUrl}
        poster={coverUrl || undefined}
        controls
        playsInline
      />
      <dl className="grid grid-cols-2 gap-3 text-xs">
        <Stat label="时长" value={`${result.duration.toFixed(2)}s`} />
        <Stat label="编码" value={result.used_hardware ? "VT GPU" : "x264"} />
        <Stat
          label="过渡"
          value={result.transitions.length ? result.transitions.join(" · ") : "—"}
        />
        <Stat label="耗时" value={`${result.runtime_seconds.toFixed(2)}s`} />
        {result.beat_grid && (
          <Stat label="BGM BPM" value={result.beat_grid.bpm.toFixed(0)} />
        )}
        {result.subtitle_max_cps !== null && (
          <Stat label="字幕峰值 CPS" value={result.subtitle_max_cps.toFixed(1)} />
        )}
      </dl>

      {videoUrl && (
        <a
          className="inline-flex items-center gap-2 self-start text-xs text-accent-300 hover:underline"
          href={videoUrl}
          download
        >
          <Download size={12} /> 下载 MP4
        </a>
      )}

      <IssueList issues={result.subtitle_issues} />

      {result.warnings.length > 0 && (
        <details className="rounded-md border border-white/5 bg-white/[0.02] p-3 text-xs">
          <summary className="cursor-pointer text-muted-foreground">
            管线警告 · {result.warnings.length} 条
          </summary>
          <ul className="mt-2 grid gap-1 pl-4 text-muted-foreground/90">
            {result.warnings.map((w, i) => (
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

function IssueList({ issues }: { issues: MixSubtitleIssue[] }) {
  if (!issues || issues.length === 0) return null;
  return (
    <ul className="grid gap-1 text-[11px]">
      {issues.map((i, idx) => (
        <li
          key={idx}
          className={cn(
            "flex items-start gap-1.5 rounded border px-2 py-1.5",
            i.severity === "fail"
              ? "border-destructive/40 bg-destructive/10 text-destructive"
              : i.severity === "warn"
                ? "border-amber-400/40 bg-amber-400/10 text-amber-200"
                : "border-white/10 bg-white/[0.02] text-muted-foreground",
          )}
        >
          <AlertTriangle size={10} className="mt-0.5 shrink-0" />
          <span>
            #{i.cue_index} · {i.message}
          </span>
        </li>
      ))}
    </ul>
  );
}

function ChipGroup<T extends { key: string; label: string }>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly T[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid gap-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => (
          <button
            key={o.key}
            type="button"
            onClick={() => onChange(o.key)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              value === o.key
                ? "border-accent-500/60 bg-accent-500/15 text-accent-200"
                : "border-white/10 bg-white/[0.02] text-muted-foreground hover:border-white/20 hover:text-foreground",
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
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
