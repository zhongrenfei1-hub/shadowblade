"use client";

import { useId, useState } from "react";
import { Play, Pause, Maximize2, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BRAND } from "@/lib/theme";

/**
 * 视频播放器占位组件。
 * 当前为纯视觉 mock — 播放/暂停切换的是 UI 状态，没有挂真实 <video>。
 * 待接入真实视频后：把 SVG 占位换成 <video ref={videoRef}>，并把按钮挂到 videoRef.play()/pause()。
 *
 * 支持可选 watermark 文案，例如 "DRAFT · v17"，在分享链接场景下用于水印。
 * 大热区按钮与底部小按钮 aria-label 区分（v1 test ring 001 P0.2 修过的 bug，
 * test ring 002 又在 share/[token] 复现，此次通过复用解决）。
 */
export function VideoPlayer({ watermark }: { watermark?: string } = {}) {
  const [playing, setPlaying] = useState(false);
  const id = useId();
  const bgId = `vp-bg-${id}`;
  const glowId = `vp-glow-${id}`;

  return (
    <div className="relative aspect-video bg-black">
      <svg
        viewBox="0 0 800 450"
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id={bgId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={BRAND.navy700} />
            <stop offset="100%" stopColor={BRAND.navy900} />
          </linearGradient>
          <radialGradient id={glowId} cx="0.65" cy="0.35" r="0.6">
            <stop offset="0%" stopColor="rgba(34,211,183,0.4)" />
            <stop offset="100%" stopColor="rgba(34,211,183,0)" />
          </radialGradient>
        </defs>
        <rect width="800" height="450" fill={`url(#${bgId})`} />
        <rect width="800" height="450" fill={`url(#${glowId})`} />
        <g transform="translate(500 225)">
          <circle r="160" fill="none" stroke="rgba(34,211,183,0.25)" strokeWidth="1" strokeDasharray="3 5" />
          <circle r="100" fill="rgba(34,211,183,0.2)" />
          <circle r="56" fill="rgba(34,211,183,0.4)" />
          <circle r="24" fill={BRAND.accent500} />
        </g>
        <text x="60" y="180" fill={BRAND.accent500} fontFamily="Inter" fontSize="11" letterSpacing="3">
          ACME · 智能腕环
        </text>
        <text x="60" y="226" fill={BRAND.paper} fontFamily="Inter Display" fontSize="38" fontWeight="700">
          你的一天，准时
        </text>
        <text x="60" y="260" fill={BRAND.graphite300} fontFamily="Inter" fontSize="14">
          无需打断节奏。
        </text>
      </svg>

      {watermark && (
        <span
          aria-hidden
          className="pointer-events-none absolute right-4 top-4 select-none rounded border border-white/20 bg-black/40 px-2 py-1 text-[10px] font-bold tracking-wider text-white/70 backdrop-blur-sm"
        >
          {watermark}
        </span>
      )}

      <button
        type="button"
        onClick={() => setPlaying((p) => !p)}
        className="absolute inset-0 grid place-items-center bg-gradient-to-b from-transparent to-black/40 transition-opacity hover:bg-black/20"
        aria-label={playing ? "切换为暂停" : "切换为播放"}
        tabIndex={-1}
      >
        {!playing && (
          <span
            aria-hidden
            className="grid h-16 w-16 place-items-center rounded-full bg-accent-500 text-navy-950 shadow-[0_16px_32px_-8px_rgba(34,211,183,0.5)]"
          >
            <Play className="h-7 w-7 fill-current" aria-hidden />
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
          {playing ? <Pause className="h-4 w-4 fill-current" aria-hidden /> : <Play className="h-4 w-4 fill-current" aria-hidden />}
        </button>
        {/* 0:16.8 / 0:28.0 是时长不是 datetime — 用 <span> 不是 <time> */}
        <span className="font-mono text-xs text-white">0:16.8</span>
        <div className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/20">
          <span className="absolute inset-y-0 left-0 w-[60%] rounded-full bg-accent-500" />
        </div>
        <span className="font-mono text-xs text-white">0:28.0</span>
        <Button size="icon" variant="ghost" aria-label="音量" className="text-white hover:bg-white/10">
          <Volume2 className="h-4 w-4" aria-hidden />
        </Button>
        <Button size="icon" variant="ghost" aria-label="全屏" className="text-white hover:bg-white/10">
          <Maximize2 className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
