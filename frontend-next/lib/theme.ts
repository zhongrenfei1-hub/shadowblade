/**
 * 设计 token · SVG 内嵌色值的中央来源
 *
 * SVG 的 fill/stroke attribute 用不上 Tailwind class，但又必须跟 tailwind config 的
 * accent / amber / navy / graphite token 保持视觉一致。这里把它们集中起来，避免硬编码漂移。
 *
 * 维护规则：tailwind.config.ts 调色板改了 → 同步这里。
 */

// 与 tailwind.config.ts → colors.* 保持像素一致。
export const BRAND = {
  // accent（青绿强调）
  accent500: "#22D3B7",
  accent400: "#2EE2C4",
  accent300: "#6EE2C5",

  // navy（深蓝）
  navy950: "#060c1a",
  navy900: "#0a1428",
  navy800: "#0f1d3a",
  navy700: "#142a55",
  navy600: "#1f3a72",
  navy500: "#2c528f",
  navy400: "#4c79b6",

  // graphite（石墨灰）
  graphite500: "#3a455c",
  graphite400: "#5a667f",
  graphite300: "#8590a8",
  graphite200: "#b6bdcc",

  // 中性
  paper: "#F7F9FC",

  // 状态强调
  sky400: "#38BDF8",
  amber400: "#FACC15",
  amber300: "#FCD34D",
  rose400: "#FB7185",
} as const;

// 视频海报 / cover 用的中央深蓝渐变端点（与 BRAND.navy700 / 950 近似但更深）
// video-player 和 share/[token] 用同一对端点保持视觉一致
export const COVER_NAVY = {
  start: "#15376a", // ≈ navy 600 / 700 中间，海报背景上端
  end: "#050a18", // ≈ 比 navy950 略黑，海报背景下端
} as const;

// KpiTile sparkline 颜色（从 tailwind palette 推导，保持像素一致）
export const TREND_COLORS = {
  positiveStroke: "rgb(110 226 197)", // accent-300
  positiveFill: "rgba(34,211,183,0.22)", // accent-500 @ 22% alpha
  negativeStroke: "rgb(252 211 77)", // amber-300
  negativeFill: "rgba(245,158,11,0.22)", // amber-500 @ 22% alpha
} as const;
