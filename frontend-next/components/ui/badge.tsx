import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "bg-secondary text-foreground/85",
        rendering: "bg-sky-500/15 text-sky-300",
        queued: "bg-amber-500/15 text-amber-300",
        running: "bg-sky-500/15 text-sky-300",
        review: "bg-violet-500/15 text-violet-300",
        scripting: "bg-violet-500/15 text-violet-300",
        storyboard: "bg-violet-500/15 text-violet-300",
        done: "bg-accent-500/15 text-accent-300",
        succeeded: "bg-accent-500/15 text-accent-300",
        draft: "bg-graphite-500/20 text-graphite-200",
        failed: "bg-rose-500/15 text-rose-300",
        rush: "bg-rose-500/15 text-rose-300",
        high: "bg-amber-500/15 text-amber-300",
        normal: "bg-graphite-500/20 text-graphite-200",
        low: "bg-graphite-700/40 text-graphite-300",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
