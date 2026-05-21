import * as React from "react";
import { cn } from "@/lib/utils";

export interface HeroIllustrationProps extends React.SVGAttributes<SVGSVGElement> {
  /** 自定义 aria-label。默认 "ShadowBlade 流水线示意"。 */
  label?: string;
}

/**
 * 工作台空状态 / 营销页面用的大插图。
 *
 * - 纯 SVG，无栅格、无远程字体、无 emoji。
 * - 沿用 `frontend/public` 静态 hero 的视觉语言：外圈虚线环 + 中心播放盘 + 四张步骤卡 + 渲染 ETA chip。
 * - 颜色统一用 Tailwind token（`text-accent-300`、`text-sky-400`、`text-violet-300`、`text-amber-300` 等），不硬编码 hex。
 * - 文字字体走继承（`font-family="inherit"`），由根布局的 Inter / PingFang SC 栈决定。
 *
 * 推荐 size：默认 `w-full max-w-[760px] aspect-[16/10]`；可通过 `className` 覆盖。
 */
export function HeroIllustration({
  className,
  label = "ShadowBlade 流水线示意",
  ...rest
}: HeroIllustrationProps) {
  return (
    <svg
      role="img"
      aria-label={label}
      viewBox="0 0 800 500"
      className={cn(
        "h-auto w-full max-w-[760px] text-foreground",
        "[&_.hf-bg]:fill-navy-950 [&_.hf-bg-2]:fill-navy-900",
        "[&_.hf-grid]:stroke-graphite-700/40",
        "[&_.hf-ring]:stroke-accent-500/55 [&_.hf-ring-mid]:stroke-accent-500/30 [&_.hf-ring-inner]:stroke-accent-500/15",
        "[&_.hf-node]:fill-accent-400",
        "[&_.hf-disk]:fill-navy-800 [&_.hf-disk]:stroke-accent-500/60",
        "[&_.hf-disk-arc]:stroke-accent-500/30",
        "[&_.hf-play]:fill-accent-400",
        "[&_.hf-card]:fill-navy-800 [&_.hf-card]:stroke-graphite-700/60",
        "[&_.hf-chip]:fill-navy-950/90 [&_.hf-chip]:stroke-accent-500/60",
        "[&_.hf-meter-bg]:fill-graphite-700/60 [&_.hf-meter-fg]:fill-accent-400",
        "[&_.hf-connector]:stroke-accent-500/40",
        "[&_.hf-label-eyebrow]:fill-muted-foreground",
        "[&_.hf-label-title]:fill-foreground",
        "[&_.hf-icon-accent]:fill-accent-500/15 [&_.hf-icon-accent]:stroke-accent-400",
        "[&_.hf-icon-sky]:fill-sky-500/15 [&_.hf-icon-sky]:stroke-sky-400",
        "[&_.hf-icon-violet]:fill-violet-500/15 [&_.hf-icon-violet]:stroke-violet-400",
        "[&_.hf-icon-amber]:fill-amber-500/15 [&_.hf-icon-amber]:stroke-amber-300",
        className
      )}
      {...rest}
    >
      {/* 背景层（用 currentColor 让 Tailwind class 接管颜色） */}
      <rect className="hf-bg" width="800" height="500" rx="20" />
      <rect className="hf-bg-2" width="800" height="500" rx="20" opacity="0.6" />

      {/* 背景网格 */}
      <g className="hf-grid" fill="none" strokeWidth="1">
        <path d="M0 100H800M0 200H800M0 300H800M0 400H800" />
        <path d="M100 0V500M200 0V500M300 0V500M400 0V500M500 0V500M600 0V500M700 0V500" />
      </g>

      {/* 右侧：流水线圆环 */}
      <g transform="translate(560 250)">
        <circle className="hf-ring" r="180" fill="none" strokeWidth="1.4" strokeDasharray="3 7" />
        <circle className="hf-ring-mid" r="135" fill="none" strokeWidth="1" />
        <circle className="hf-ring-inner" r="90" fill="none" strokeWidth="1" />

        {/* 环上的步骤节点 */}
        <g className="hf-node">
          <circle cx="0" cy="-180" r="4.5" />
          <circle cx="171" cy="-55" r="4.5" />
          <circle cx="106" cy="146" r="4.5" />
          <circle cx="-106" cy="146" r="4.5" />
          <circle cx="-171" cy="-55" r="4.5" />
        </g>

        {/* 中心播放盘 */}
        <circle className="hf-disk" r="52" strokeWidth="1.4" />
        <circle
          className="hf-disk-arc"
          r="52"
          fill="none"
          strokeWidth="10"
          strokeDasharray="120 380"
          strokeDashoffset="-72"
        />
        <path className="hf-play" d="M-12 -16L22 0L-12 16Z" />
        <text
          y="38"
          textAnchor="middle"
          fontSize="9"
          fontWeight="600"
          letterSpacing="2.4"
          className="hf-label-eyebrow"
          fontFamily="inherit"
        >
          流水线
        </text>
      </g>

      {/* 步骤卡 01：简报与品牌 */}
      <StepCard x={36} y={70} index="01" title="简报与品牌套件" iconClass="hf-icon-accent">
        <path d="M30 36h20M30 44h14" strokeWidth="1.5" />
      </StepCard>

      {/* 步骤卡 02：分镜与配音 */}
      <StepCard x={36} y={186} index="02" title="分镜与配音" iconClass="hf-icon-sky">
        <path d="M28 32l10 8 10-8M28 42l10 8 10-8" strokeWidth="1.5" fill="none" />
      </StepCard>

      {/* 步骤卡 03：合成与字幕 */}
      <StepCard x={36} y={302} index="03" title="合成与字幕" iconClass="hf-icon-violet">
        <path d="M28 30h24M28 38h18M28 46h22" strokeWidth="1.5" />
      </StepCard>

      {/* 步骤卡 04：渲染与交付 */}
      <StepCard x={36} y={418} index="04" title="渲染与交付" iconClass="hf-icon-amber" cardWidth={260} cardHeight={62}>
        <path d="M40 28l8 12-8 12-8-12Z" fill="none" strokeWidth="1.5" />
      </StepCard>

      {/* 连接线：从卡片连到圆环 */}
      <g className="hf-connector" fill="none" strokeWidth="1" strokeDasharray="3 5">
        <path d="M296 108 Q 400 120 460 170" />
        <path d="M296 218 Q 400 230 470 235" />
        <path d="M296 334 Q 400 320 470 290" />
        <path d="M296 446 Q 400 420 460 350" />
      </g>

      {/* 渲染 ETA chip */}
      <g transform="translate(644 188)">
        <rect className="hf-chip" width="140" height="48" rx="10" strokeWidth="1" />
        <circle cx="18" cy="24" r="4" className="fill-accent-400" />
        <circle cx="18" cy="24" r="7.5" fill="none" strokeWidth="1.2" className="stroke-accent-500/40" />
        <text
          x="32"
          y="20"
          fontSize="9"
          fontWeight="600"
          letterSpacing="2"
          className="hf-label-eyebrow"
          fontFamily="inherit"
        >
          渲染中
        </text>
        <text
          x="32"
          y="38"
          fontSize="15"
          fontWeight="700"
          className="hf-label-title"
          fontFamily="inherit"
        >
          预计 64 秒
        </text>
      </g>

      {/* 合成进度小卡 */}
      <g transform="translate(338 200)">
        <rect className="hf-chip" width="170" height="62" rx="10" strokeWidth="1" />
        <text
          x="14"
          y="20"
          fontSize="9"
          fontWeight="600"
          letterSpacing="2.2"
          className="hf-label-eyebrow"
          fontFamily="inherit"
        >
          合成
        </text>
        <text
          x="14"
          y="38"
          fontSize="14"
          fontWeight="700"
          className="hf-label-title"
          fontFamily="inherit"
        >
          已完成 62%
        </text>
        <rect className="hf-meter-bg" x="14" y="46" width="142" height="6" rx="3" />
        <rect className="hf-meter-fg" x="14" y="46" width="88" height="6" rx="3" />
      </g>
    </svg>
  );
}

interface StepCardProps {
  x: number;
  y: number;
  index: string;
  title: string;
  iconClass: string;
  cardWidth?: number;
  cardHeight?: number;
  children?: React.ReactNode;
}

function StepCard({
  x,
  y,
  index,
  title,
  iconClass,
  cardWidth = 260,
  cardHeight = 62,
  children,
}: StepCardProps) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect className="hf-card" width={cardWidth} height={cardHeight} rx="12" strokeWidth="1" />
      <rect className={iconClass} x="14" y="14" width="34" height="34" rx="8" strokeWidth="1.4" fill="none" />
      <g className={iconClass} transform="translate(-2 -2)" stroke="currentColor">
        {children}
      </g>
      <text
        x="62"
        y="26"
        fontSize="9"
        fontWeight="600"
        letterSpacing="2.4"
        className="hf-label-eyebrow"
        fontFamily="inherit"
      >
        步骤 {index}
      </text>
      <text
        x="62"
        y="46"
        fontSize="14"
        fontWeight="600"
        className="hf-label-title"
        fontFamily="inherit"
      >
        {title}
      </text>
    </g>
  );
}
