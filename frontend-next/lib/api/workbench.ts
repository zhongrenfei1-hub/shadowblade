/**
 * Workbench API client — Studio 工作台聚合端点。
 *
 * 后端：`/api/v1/workbench/{overview,recent-projects,active-tasks}`。
 * 全部从已有资源派生（Project / Job / RenderTask / BrandKit / mix-video
 * tasks），不引入新表。
 */

export interface WorkbenchKpi {
  key: string;
  label: string;
  value: number;
  unit: string;
}

export interface WorkbenchBrandKit {
  id: number;
  name: string;
  scope: string;
  primary_color: string;
  accent_color: string;
  secondary_color: string;
  font_heading: string;
  font_body: string;
  logo_url: string | null;
  voice: string;
  watermark_position: string;
  is_active: boolean;
}

export interface WorkbenchTemplate {
  name: string;
  version: string;
  description: string;
  tags: string[];
}

export interface WorkbenchOverview {
  workspace_id: number;
  generated_at: string;
  kpis: WorkbenchKpi[];
  brand_kit: WorkbenchBrandKit | null;
  featured_templates: WorkbenchTemplate[];
  quick_actions?: { label: string; href: string }[];
}

export interface RecentProject {
  id: number;
  name: string;
  purpose: "marketing" | "training" | "product_demo" | "social";
  status: string;
  aspect_ratio: string;
  duration_seconds: number;
  voice: string;
  brief: string;
  cover_url: string | null;
  updated_at: string;
  created_at: string;
  href_open: string;
  href_detail: string;
}

export interface ActiveTask {
  task_id: string;
  source: "render_queue" | "mix_video";
  project_id: number;
  project_name: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  priority: "rush" | "high" | "normal" | "low";
  estimated_seconds: number;
  worker: string | null;
  output_url: string | null;
  queued_at: string;
  started_at: string | null;
  finished_at: string | null;
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
    throw new Error(`workbench ${res.status} ${path}`);
  }
  return res.json() as Promise<T>;
}

export function getOverview(): Promise<WorkbenchOverview> {
  return get<WorkbenchOverview>("/workbench/overview");
}

export function listRecentProjects(): Promise<{ items: RecentProject[] }> {
  return get<{ items: RecentProject[] }>("/workbench/recent-projects");
}

export function listActiveTasks(): Promise<{
  workspace_id: number;
  generated_at: string;
  items: ActiveTask[];
}> {
  return get("/workbench/active-tasks");
}
