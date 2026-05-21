/**
 * 设计 token · SVG 内嵌色值的中央来源
 *
 * SVG 的 fill/stroke attribute 用不上 Tailwind class，但又必须跟 tailwind config 的
 * accent / amber / navy / graphite token 保持视觉一致。这里把它们集中起来，避免硬编码漂移。
 *
 * 维护规则：tailwind.config.ts 调色板改了 → 同步这里。
 */

// 与 tailwind.config.ts → colors.accent / amber / 等保持像素一致。
export const BRAND = {
  accent500: "#22D3B7",
  accent400: "#2EE2C4",
  accent300: "#6EE2C5",
  navy900: "#0a1428",
  navy800: "#0f1d3a",
  navy700: "#142a55",
  navy500: "#2c528f",
  paper: "#F7F9FC",
  graphite300: "#8590a8",
  sky400: "#38BDF8",
  amber400: "#FACC15",
  amber300: "#FCD34D",
} as const;

// KpiTile sparkline 颜色（从 tailwind palette 推导，保持像素一致）
export const TREND_COLORS = {
  positiveStroke: "rgb(110 226 197)", // accent-300
  positiveFill: "rgba(34,211,183,0.22)", // accent-500 @ 22% alpha
  negativeStroke: "rgb(252 211 77)", // amber-300
  negativeFill: "rgba(245,158,11,0.22)", // amber-500 @ 22% alpha
} as const;
