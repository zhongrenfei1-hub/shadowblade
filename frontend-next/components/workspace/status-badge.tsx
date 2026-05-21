import { Badge, type BadgeProps } from "@/components/ui/badge";
import { STATUS_LABEL, type Status } from "@/lib/api";

const DOT_COLOR: Partial<Record<Status, string>> = {
  rendering: "bg-sky-400",
  queued: "bg-amber-400",
  scripting: "bg-violet-400",
  storyboard: "bg-violet-400",
  review: "bg-violet-400",
  done: "bg-accent-400",
  draft: "bg-graphite-300",
  failed: "bg-rose-400",
};

const PULSE: Partial<Record<Status, boolean>> = {
  rendering: true,
  scripting: true,
  storyboard: true,
};

export function StatusBadge({ status }: { status: Status }) {
  const dot = DOT_COLOR[status] ?? "bg-graphite-300";
  return (
    <Badge variant={status as BadgeProps["variant"]}>
      <span
        aria-hidden
        className={`inline-block h-1.5 w-1.5 rounded-full ${dot} ${PULSE[status] ? "animate-pulse-ring" : ""}`}
      />
      {STATUS_LABEL[status]}
    </Badge>
  );
}
