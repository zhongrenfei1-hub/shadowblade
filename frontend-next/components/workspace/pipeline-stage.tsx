import { cn } from "@/lib/utils";
import { Check, Loader2 } from "lucide-react";

export function PipelineStage({
  index,
  title,
  log,
  meta,
  state,
  progress,
}: {
  index: string | number;
  title: string;
  log: string;
  meta: string;
  state?: "succeeded" | "running" | "queued";
  progress?: number;
}) {
  const running = state === "running";
  return (
    <div
      className={cn(
        "relative grid grid-cols-[28px_1fr_auto] items-center gap-3 overflow-hidden rounded-md border border-border bg-card/50 px-4 py-3 transition-colors",
        running && "border-sky-500/35 bg-sky-500/[0.05] shadow-[0_0_0_1px_rgba(56,189,248,0.15)_inset]"
      )}
    >
      {running && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-y-0 left-0 w-full origin-left bg-gradient-to-r from-sky-500/[0.18] via-sky-500/[0.08] to-transparent animate-shimmer-slow"
        />
      )}
      <span
        className={cn(
          "relative grid h-6 w-6 place-items-center rounded-md font-mono text-[11px]",
          state === "succeeded" && "bg-accent-500/20 text-accent-300",
          running && "bg-sky-500/25 text-sky-200 ring-2 ring-sky-500/40",
          !state && "bg-white/[0.04] text-muted-foreground"
        )}
        aria-hidden
      >
        {state === "succeeded" ? (
          <Check className="h-3 w-3" />
        ) : running ? (
          <Loader2 className="preserve-motion h-3 w-3 animate-spin" />
        ) : typeof index === "string" ? (
          index
        ) : (
          String(index).padStart(2, "0")
        )}
      </span>
      <div className="relative min-w-0">
        <div className="flex items-center gap-2 text-sm font-semibold">
          {title}
          {running && (
            <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-sky-300">运行中</span>
          )}
        </div>
        <div className="truncate font-mono text-[11px] text-muted-foreground">{log}</div>
        {running && typeof progress === "number" && (
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-sky-500/15">
            <span
              className="block h-full rounded-full bg-gradient-to-r from-sky-400 to-accent-400 transition-[width] duration-700"
              style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
            />
          </div>
        )}
      </div>
      <div className="relative text-right text-xs text-muted-foreground num">{meta}</div>
    </div>
  );
}
