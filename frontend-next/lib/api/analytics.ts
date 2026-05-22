/**
 * Analytics API client — live 实现（取代之前 fixture）。
 *
 * 后端：`/api/v1/analytics/{overview,trends,videos,templates,brand-kits,team,export}`
 * 旧 showcase 走 `?legacy=true` 回退到 fixture。
 */

export interface AnalyticsKpi {
  key: string;
  label: string;
  value: number;
  unit: string;
  delta: number | null;
}

export interface AnalyticsBucket {
  label: string;
  value: number;
}

export interface AnalyticsOverview {
  workspace_id: number;
  period: string;
  generated_at: string;
  from: string;
  to: string;
  cached: boolean;
  kpis: AnalyticsKpi[];
  distribution: AnalyticsBucket[];
  status_distribution: AnalyticsBucket[];
  totals: Record<string, number>;
}

export interface TrendPoint {
  bucket: string;
  videos: number;
  renders: number;
  success: number;
  failures: number;
}

export interface AnalyticsTrends {
  workspace_id: number;
  period: string;
  granularity: "day" | "week" | "month";
  points: TrendPoint[];
}

const IS_SERVER = typeof window === "undefined";
const SERVER_BASE = process.env.BACKEND_URL || "http://localhost:8000";
const BASE = IS_SERVER
  ? `${SERVER_BASE}/api/v1`
  : process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "/api/v1";

const HEADERS = { "X-Workspace-Id": "1", "X-User-Id": "1" };

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    headers: HEADERS,
  });
  if (!res.ok) {
    throw new Error(`analytics ${res.status} ${path}`);
  }
  return res.json() as Promise<T>;
}

export function getOverview(
  period: "7d" | "30d" | "90d" = "30d",
): Promise<AnalyticsOverview> {
  return get<AnalyticsOverview>(`/analytics/overview?period=${period}`);
}

export function getTrends(
  period: "7d" | "30d" | "90d" = "30d",
): Promise<AnalyticsTrends> {
  return get<AnalyticsTrends>(`/analytics/trends?period=${period}`);
}
