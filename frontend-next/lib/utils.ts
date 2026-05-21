import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds} 秒`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s ? `${m} 分 ${s} 秒` : `${m} 分钟`;
}

export function relativeTime(iso: string | Date | undefined | null) {
  if (!iso) return "";
  const date = typeof iso === "string" ? new Date(iso) : iso;
  const diff = (Date.now() - date.getTime()) / 60000;
  if (diff < 1) return "刚刚";
  if (diff < 60) return `${Math.round(diff)} 分钟前`;
  if (diff < 60 * 24) return `${Math.round(diff / 60)} 小时前`;
  if (diff < 60 * 24 * 7) return `${Math.round(diff / 60 / 24)} 天前`;
  return date.toLocaleDateString("zh-CN");
}
