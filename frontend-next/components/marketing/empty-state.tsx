import * as React from "react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface EmptyStateAction {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: "default" | "outline" | "ghost";
}

export interface EmptyStateProps extends React.HTMLAttributes<HTMLElement> {
  /** 主图标（lucide-react），居中放在 accent-cyan 描边圆环内 */
  icon: LucideIcon;
  /** 一句话标题，14 字内最佳 */
  title: string;
  /** 一句话描述，说明下一步可以做什么 */
  description: string;
  /** 主操作按钮；如需双按钮传 `secondaryAction` */
  action?: EmptyStateAction;
  /** 次操作（可选），渲染为 outline 按钮 */
  secondaryAction?: EmptyStateAction;
}

/**
 * 通用空状态组件。
 *
 * - 居中布局，垂直堆叠：圆环图标 → 标题 → 描述 → CTA。
 * - 圆环使用 `accent-cyan` 描边 + 微光晕，呼应 dashboard 的视觉锚点。
 * - 文案规则参考 `components/marketing/copywriting.ts` 的 `EMPTY_STATES`。
 *
 * @example
 * ```tsx
 * <EmptyState
 *   icon={FolderPlus}
 *   title="还没有项目"
 *   description="新建一个项目，开始你的第一条成片。"
 *   action={{ label: "新建项目", href: "/create" }}
 * />
 * ```
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className,
  ...rest
}: EmptyStateProps) {
  // 不再用 role="status" + aria-live — 否则 filter 切换会被 SR 反复念出
  // （test ring 003 P2.27 反馈）。空态作为普通 section 即可。
  return (
    <section
      aria-label={title}
      className={cn(
        "grid place-items-center gap-5 rounded-xl border border-border bg-card/40 px-6 py-14 text-center backdrop-blur-sm",
        className
      )}
      {...rest}
    >
      <div
        aria-hidden
        className="relative grid h-20 w-20 place-items-center rounded-full border border-accent-500/45 bg-accent-500/5 shadow-[0_0_0_6px_rgba(34,211,183,0.06),0_18px_42px_-18px_rgba(34,211,183,0.45)]"
      >
        <span className="pointer-events-none absolute inset-0 rounded-full bg-[radial-gradient(circle,rgba(34,211,183,0.18),transparent_65%)]" />
        <Icon className="relative h-8 w-8 text-accent-300" strokeWidth={1.6} />
      </div>

      <div className="grid gap-1.5">
        <h3 className="font-display text-lg font-semibold tracking-tight text-foreground">
          {title}
        </h3>
        <p className="mx-auto max-w-prose text-sm text-muted-foreground text-balance">
          {description}
        </p>
      </div>

      {(action || secondaryAction) && (
        <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
          {action && <ActionButton {...action} />}
          {secondaryAction && (
            <ActionButton variant="outline" {...secondaryAction} />
          )}
        </div>
      )}
    </section>
  );
}

function ActionButton({ label, href, onClick, variant = "default" }: EmptyStateAction) {
  if (href) {
    return (
      <Button asChild variant={variant}>
        <a href={href}>{label}</a>
      </Button>
    );
  }
  return (
    <Button variant={variant} onClick={onClick}>
      {label}
    </Button>
  );
}
