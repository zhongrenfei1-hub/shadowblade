import { cn } from "@/lib/utils";
import { BRAND } from "@/lib/theme";
import { useId } from "react";

/**
 * ShadowBlade 品牌符号（小箭头标志）
 * sidebar / mobile-sidebar / 任意需要 logo 的位置共用此组件，避免 svg + hex 多处重复。
 */
export function BrandMark({ className }: { className?: string }) {
  const id = useId();
  const gradId = `sb-mark-${id}`;
  return (
    <span
      className={cn(
        "grid h-8 w-8 place-items-center rounded-md border border-accent-500/30 bg-gradient-to-br from-navy-700 to-navy-900 shadow-[0_4px_12px_rgba(34,211,183,0.18)]",
        className
      )}
    >
      <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" aria-hidden>
        <path d="M4 4L20 12L4 20V14L12 12L4 10V4Z" fill={`url(#${gradId})`} />
        <defs>
          <linearGradient id={gradId} x1="4" y1="4" x2="20" y2="20">
            <stop offset="0%" stopColor={BRAND.accent500} />
            <stop offset="100%" stopColor={BRAND.sky400} />
          </linearGradient>
        </defs>
      </svg>
    </span>
  );
}
