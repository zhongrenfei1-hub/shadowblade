"use client";

import { useId } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";
import { TREND_COLORS } from "@/lib/theme";

// 当 trend prop 缺失时的占位序列（保持视觉节奏，不代表真实数据）。
// 应当尽可能从父层传入真实 trend；占位仅用于早期 mock。
const FALLBACK_TREND = [4, 6, 5, 7, 8, 7, 9];

function describeTrend(values: number[]): string {
  if (values.length < 2) return "趋势平稳";
  const head = values.slice(0, Math.floor(values.length / 2));
  const tail = values.slice(Math.floor(values.length / 2));
  const avgHead = head.reduce((a, b) => a + b, 0) / head.length;
  const avgTail = tail.reduce((a, b) => a + b, 0) / tail.length;
  const delta = avgTail - avgHead;
  const ratio = avgHead === 0 ? 0 : delta / avgHead;
  if (Math.abs(ratio) < 0.03) return "近 7 期趋势平稳";
  return ratio > 0 ? "近 7 期持续上升" : "近 7 期持续下降";
}

export function KpiTile({
  icon: Icon,
  label,
  value,
  suffix,
  delta,
  positive = true,
  trend,
  srHint,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  suffix?: string;
  delta: string;
  positive?: boolean;
  trend?: number[];
  srHint?: string;
}) {
  const reactId = useId();
  const DeltaIcon = positive ? ArrowUpRight : ArrowDownRight;
  const usingFallback = !(trend && trend.length > 1);
  const sparkline = usingFallback ? FALLBACK_TREND : (trend as number[]);
  const max = Math.max(...sparkline);
  const min = Math.min(...sparkline);
  const range = max - min || 1;
  const stroke = positive ? TREND_COLORS.positiveStroke : TREND_COLORS.negativeStroke;
  const fillStop = positive ? TREND_COLORS.positiveFill : TREND_COLORS.negativeFill;
  const gradientId = `kpi-grad-${reactId}`;
  const hint = srHint ?? `${label} ${value}${suffix ?? ""}，${delta}，${describeTrend(sparkline)}`;

  return (
    <Card className="group relative grid gap-3 overflow-hidden p-5 transition-colors hover:border-accent-500/30">
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_100%_0%,rgba(34,211,183,0.1),transparent_55%)] opacity-90 transition-opacity group-hover:opacity-100"
      />
      <div className="flex items-center justify-between gap-2 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <Icon className="h-3.5 w-3.5 opacity-70" aria-hidden />
          <span className="text-[12px] uppercase tracking-[0.08em]">{label}</span>
        </span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <div className="font-display text-[34px] font-semibold leading-none tracking-tight num">
          {value}
          {suffix && <small className="ml-1 text-base font-medium text-muted-foreground">{suffix}</small>}
        </div>
        <svg
          viewBox="0 0 80 32"
          preserveAspectRatio="none"
          aria-hidden
          className="h-9 w-[78px] shrink-0 opacity-90"
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={fillStop} />
              <stop offset="100%" stopColor="rgba(0,0,0,0)" />
            </linearGradient>
          </defs>
          {(() => {
            const pts = sparkline
              .map((v, i) => {
                const x = (i / (sparkline.length - 1)) * 80;
                const y = 30 - ((v - min) / range) * 26 - 2;
                return `${x.toFixed(1)},${y.toFixed(1)}`;
              })
              .join(" ");
            return (
              <>
                <polyline points={`0,32 ${pts} 80,32`} fill={`url(#${gradientId})`} />
                <polyline
                  points={pts}
                  fill="none"
                  stroke={stroke}
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </>
            );
          })()}
        </svg>
      </div>
      <span
        className={cn(
          "inline-flex w-max items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold num",
          positive ? "bg-accent-500/12 text-accent-300" : "bg-amber-500/15 text-amber-300"
        )}
      >
        <DeltaIcon className="h-3 w-3" aria-hidden />
        {delta}
      </span>
      <span className="sr-only">{hint}</span>
    </Card>
  );
}
