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
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  suffix?: string;
  delta: string;
  positive?: boolean;
}) {
  const DeltaIcon = positive ? ArrowUpRight : ArrowDownRight;
  return (
    <Card className="relative grid gap-3 overflow-hidden p-5">
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_100%_0%,rgba(34,211,183,0.08),transparent_50%)]"
      />
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-3.5 w-3.5" aria-hidden />
        <span>{label}</span>
      </div>
      <div className="font-display text-3xl font-semibold tracking-tight num">
        {value}
        {suffix && <small className="ml-1.5 text-base font-medium text-muted-foreground">{suffix}</small>}
      </div>
      <span
        className={cn(
          "inline-flex w-max items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold num",
          positive ? "bg-accent-500/10 text-accent-300" : "bg-amber-500/15 text-amber-300"
        )}
      >
        <DeltaIcon className="h-3 w-3" />
        {delta}
      </span>
    </Card>
  );
}
