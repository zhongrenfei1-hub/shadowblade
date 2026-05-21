import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";

export function KpiTile({
  icon: Icon,
  label,
  value,
  suffix,
  delta,
  positive = true,
  trend,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  suffix?: string;
  delta: string;
  positive?: boolean;
  trend?: number[];
}) {
  const DeltaIcon = positive ? ArrowUpRight : ArrowDownRight;
  const sparkline = trend && trend.length > 1 ? trend : [4, 6, 5, 7, 8, 7, 9];
  const max = Math.max(...sparkline);
  const min = Math.min(...sparkline);
  const range = max - min || 1;
  const stroke = positive ? "rgb(125 232 207)" : "rgb(252 211 77)";
  const fill = positive ? "rgba(34,211,183,0.22)" : "rgba(245,158,11,0.22)";

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
            <linearGradient id={`kpi-grad-${label}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={fill} />
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
                <polyline
                  points={`0,32 ${pts} 80,32`}
                  fill={`url(#kpi-grad-${label})`}
                />
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
        <DeltaIcon className="h-3 w-3" />
        {delta}
      </span>
    </Card>
  );
}
