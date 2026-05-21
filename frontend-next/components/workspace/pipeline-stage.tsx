import { cn } from "@/lib/utils";
import { Check, Circle, Loader2 } from "lucide-react";

export function PipelineStage({
  index,
  title,
  log,
  meta,
  state,
}: {
  index: string | number;
  title: string;
  log: string;
  meta: string;
  state?: "succeeded" | "running" | "queued";
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[28px_1fr_auto] items-center gap-3 rounded-md border border-border bg-card/50 px-4 py-3",
        state === "running" && "border-sky-500/30 bg-sky-500/[0.04]"
      )}
    >
      <span
        className={cn(
          "grid h-6 w-6 place-items-center rounded-md font-mono text-[11px]",
          state === "succeeded" && "bg-accent-500/20 text-accent-300",
          state === "running" && "bg-sky-500/20 text-sky-300",
          !state && "bg-white/[0.04] text-muted-foreground"
        )}
        aria-hidden
      >
        {state === "succeeded" ? (
          <Check className="h-3 w-3" />
        ) : state === "running" ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : typeof index === "string" ? (
          index
        ) : (
          String(index).padStart(2, "0")
        )}
      </span>
      <div className="min-w-0">
        <div className="text-sm font-semibold">{title}</div>
        <div className="truncate font-mono text-[11px] text-muted-foreground">{log}</div>
      </div>
      <div className="text-right text-xs text-muted-foreground num">{meta}</div>
    </div>
  );
}
