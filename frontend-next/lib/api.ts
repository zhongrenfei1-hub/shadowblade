/**
 * 调 FastAPI 后端的薄客户端。
 * 走 next.config.mjs 的 rewrite，所以 client 侧统一用相对路径 /api/v1/*。
 * 服务端组件直接打 backend；客户端组件用相对路径即可。
 */

const BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

async function get<T>(path: string, fallback?: T, init?: RequestInit): Promise<T> {
  try {
    const res = await fetch(`${BASE}${path}`, { cache: "no-store", ...init });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  } catch (err) {
    if (fallback !== undefined) {
      // 开发环境：明确告诉作者后端没接通，正在用 fallback。
      // 生产环境：静默回退，避免噪音。
      if (process.env.NODE_ENV !== "production") {
        // eslint-disable-next-line no-console
        console.warn(`[api] ${path} 走 fallback：`, err);
      }
      return fallback;
    }
    throw err;
  }
}

// ─── 类型 ─────────────────────────────────────────────────────────────

export type Status =
  | "draft"
  | "scripting"
  | "storyboard"
  | "rendering"
  | "review"
  | "done"
  | "failed"
  | "queued"
  | "running"
  | "succeeded";

export const STATUS_LABEL: Record<Status, string> = {
  draft: "草稿",
  scripting: "撰写脚本",
  storyboard: "分镜",
  rendering: "渲染中",
  review: "待审核",
  done: "已完成",
  failed: "失败",
  queued: "排队中",
  running: "运行中",
  succeeded: "成功",
};

export type Project = {
  id: number;
  name: string;
  purpose: "marketing" | "training" | "product_demo" | "social";
  status: Status;
  progress: number;
  aspect_ratio: string;
  duration_seconds: number;
  owner: string;
  updated_at: string;
  cover: string;
  tags?: string[];
};

export type Job = {
  id: number;
  project_id: number;
  stage: "script" | "storyboard" | "tts" | "b_roll" | "compose" | "render";
  status: Status;
  progress: number;
  runtime_seconds: number;
  log_tail: string;
};

export type Asset = {
  id: number;
  name: string;
  // 与 backend/services/fixtures.py 对齐：logo 用 "image" + slug 前缀区分。
  kind: "video" | "image" | "audio" | "font";
  slug: string;
  size_bytes: number;
  tags: string[];
  created_at: string;
};

export type Template = {
  id: number;
  slug: string;
  name: string;
  category: "marketing" | "training" | "product_demo" | "social";
  aspect_ratio: string;
  duration_seconds: number;
  scenes: number;
};

export type RenderTask = {
  id: number;
  project: string;
  priority: "rush" | "high" | "normal" | "low";
  status: Status;
  progress: number;
  eta_seconds: number;
  worker: string | null;
};

export type Workspace = {
  id: number;
  slug: string;
  name: string;
  plan: string;
  seats: number;
  monthly_render_quota: number;
  monthly_render_used: number;
  team: { id: number; name: string; role: string }[];
};

export type Analytics = {
  kpis: { label: string; value: number; delta: number; unit: string }[];
  timeseries: { day: string; rendered: number; approved: number; rejected: number }[];
  distribution: { label: string; value: number }[];
};

export type BrandKit = {
  id: number;
  name: string;
  primary_color: string;
  accent_color: string;
  font_heading: string;
  font_body: string;
  voice: string;
  tone: {
    voice_profile: string;
    do: string[];
    avoid: string[];
  };
};

// ─── 调用 ─────────────────────────────────────────────────────────────

export const api = {
  health: () => get<{ status: string; service: string; version: string }>("/health"),
  workspace: () =>
    get<Workspace>("/workspaces/me", {
      id: 1,
      slug: "acme",
      name: "Acme Marketing Cloud",
      plan: "scale",
      seats: 24,
      monthly_render_quota: 1000,
      monthly_render_used: 387,
      team: [
        { id: 1, name: "Ava Chen", role: "工作空间管理员" },
        { id: 2, name: "Marcus Lee", role: "制作人" },
        { id: 3, name: "Priya Rao", role: "品牌负责人" },
        { id: 4, name: "Diego Alvarez", role: "审核员" },
      ],
    }),
  projects: () =>
    get<{ items: Project[]; total: number }>("/projects", { items: PROJECT_FALLBACK, total: 38 }),
  project: (id: number) =>
    get<Project | { error: string }>(`/projects/${id}`, PROJECT_FALLBACK[0]),
  jobs: () => get<{ items: Job[] }>("/jobs", { items: JOB_FALLBACK }),
  assets: () =>
    get<{ items: Asset[]; totals: Record<string, number> }>("/assets", {
      items: ASSET_FALLBACK,
      // 与 backend fixtures 对齐：logo 计入 image，但 totals 仍保留 logo 维度供 UI 显示。
      totals: { video: 14, image: 86, audio: 9, font: 4, logo: 3 },
    }),
  templates: () => get<{ items: Template[] }>("/templates", { items: TEMPLATE_FALLBACK }),
  renderQueue: () =>
    get<{ concurrency: number; items: RenderTask[] }>("/render-queue", {
      concurrency: 4,
      items: QUEUE_FALLBACK,
    }),
  brandKits: () => get<{ items: BrandKit[] }>("/brand-kits", { items: BRAND_KIT_FALLBACK }),
  analytics: () => get<Analytics>("/analytics/overview", ANALYTICS_FALLBACK),
};

// ─── 离线回退数据（与后端 fixtures 一致）─────────────────────────────

const PROJECT_FALLBACK: Project[] = [
  { id: 101, name: "春季产品发布 — 智能腕环", purpose: "marketing", status: "rendering", progress: 0.62, aspect_ratio: "9:16", duration_seconds: 28, owner: "Ava Chen", updated_at: new Date(Date.now() - 9 * 60_000).toISOString(), cover: "wearable-hub", tags: ["主推", "付费社媒"] },
  { id: 102, name: "入职培训 · 销售工程师训练营", purpose: "training", status: "review", progress: 1.0, aspect_ratio: "16:9", duration_seconds: 96, owner: "Marcus Lee", updated_at: new Date(Date.now() - 44 * 60_000).toISOString(), cover: "bootcamp", tags: ["内部"] },
  { id: 103, name: "AI Copilot · 60 秒产品演示", purpose: "product_demo", status: "scripting", progress: 0.18, aspect_ratio: "16:9", duration_seconds: 60, owner: "Priya Rao", updated_at: new Date(Date.now() - 180 * 60_000).toISOString(), cover: "copilot", tags: ["销售", "演示"] },
  { id: 104, name: "TikTok 预告 — C 轮发布", purpose: "social", status: "done", progress: 1.0, aspect_ratio: "9:16", duration_seconds: 15, owner: "Diego Alvarez", updated_at: new Date(Date.now() - 1440 * 60_000).toISOString(), cover: "series-c", tags: ["社交"] },
  { id: 105, name: "Q3 客户故事 — Helios Logistics", purpose: "marketing", status: "draft", progress: 0.04, aspect_ratio: "16:9", duration_seconds: 75, owner: "Ava Chen", updated_at: new Date(Date.now() - 2 * 60_000).toISOString(), cover: "helios", tags: ["客户案例"] },
  { id: 106, name: "合规培训 — GDPR 要点", purpose: "training", status: "draft", progress: 0, aspect_ratio: "16:9", duration_seconds: 180, owner: "Marcus Lee", updated_at: new Date(Date.now() - 720 * 60_000).toISOString(), cover: "gdpr", tags: ["合规"] },
];

const JOB_FALLBACK: Job[] = [
  { id: 1, project_id: 101, stage: "script", status: "succeeded", progress: 1, runtime_seconds: 8.4, log_tail: "scene_count=6 voice=alloy-en-female" },
  { id: 2, project_id: 101, stage: "storyboard", status: "succeeded", progress: 1, runtime_seconds: 12.1, log_tail: "分镜已渲染 6/6 · style=editorial" },
  { id: 3, project_id: 101, stage: "tts", status: "succeeded", progress: 1, runtime_seconds: 18.6, log_tail: "配音 4 个版本 · 响度 -14 LUFS" },
  { id: 4, project_id: 101, stage: "b_roll", status: "succeeded", progress: 1, runtime_seconds: 41, log_tail: "空镜素材匹配 18 段 · CC 协议" },
  { id: 5, project_id: 101, stage: "compose", status: "running", progress: 0.62, runtime_seconds: 73, log_tail: "合成 62% · 等待叠加层 #3" },
  { id: 6, project_id: 101, stage: "render", status: "queued", progress: 0, runtime_seconds: 0, log_tail: "排在 2 个加急任务之后" },
];

const ASSET_FALLBACK: Asset[] = [
  { id: 1, name: "品牌 logo · 主色", kind: "image", slug: "logo-primary", size_bytes: 48_212, tags: ["品牌", "已审核"], created_at: new Date().toISOString() },
  { id: 2, name: "品牌 logo · 单色", kind: "image", slug: "logo-mono", size_bytes: 41_900, tags: ["品牌", "已审核"], created_at: new Date().toISOString() },
  { id: 3, name: "创始人空镜 · 主题演讲", kind: "video", slug: "founder-keynote", size_bytes: 184_300_000, tags: ["资源库"], created_at: new Date().toISOString() },
  { id: 4, name: "配音 · Ava 旁白", kind: "audio", slug: "voice-ava", size_bytes: 5_840_000, tags: ["资源库"], created_at: new Date().toISOString() },
  { id: 5, name: "产品 UI · 工作台", kind: "image", slug: "ui-dashboard", size_bytes: 612_440, tags: ["资源库"], created_at: new Date().toISOString() },
  { id: 6, name: "产品 UI · 编辑器", kind: "image", slug: "ui-studio", size_bytes: 588_212, tags: ["资源库"], created_at: new Date().toISOString() },
  { id: 7, name: "素材 · 城市天际线", kind: "video", slug: "skyline", size_bytes: 92_111_000, tags: ["资源库"], created_at: new Date().toISOString() },
  { id: 8, name: "素材 · 机房推轨", kind: "video", slug: "server-room", size_bytes: 88_900_000, tags: ["资源库"], created_at: new Date().toISOString() },
  { id: 9, name: "字体 · Inter Display", kind: "font", slug: "inter-display", size_bytes: 412_000, tags: ["资源库"], created_at: new Date().toISOString() },
  { id: 10, name: "字体 · JetBrains Mono", kind: "font", slug: "jetbrains-mono", size_bytes: 388_000, tags: ["资源库"], created_at: new Date().toISOString() },
];

const TEMPLATE_FALLBACK: Template[] = [
  { id: 1, slug: "hero-launch", name: "发布主推 · 30 秒", category: "marketing", aspect_ratio: "9:16", duration_seconds: 30, scenes: 4 },
  { id: 2, slug: "product-explainer", name: "产品讲解 · 60 秒", category: "product_demo", aspect_ratio: "16:9", duration_seconds: 60, scenes: 5 },
  { id: 3, slug: "training-module", name: "培训模块 · 3 分钟", category: "training", aspect_ratio: "16:9", duration_seconds: 180, scenes: 6 },
  { id: 4, slug: "social-teaser", name: "社交预告 · 15 秒", category: "social", aspect_ratio: "9:16", duration_seconds: 15, scenes: 4 },
  { id: 5, slug: "case-study", name: "客户案例 · 75 秒", category: "marketing", aspect_ratio: "16:9", duration_seconds: 75, scenes: 5 },
  { id: 6, slug: "onboarding-loop", name: "入职循环 · 45 秒", category: "training", aspect_ratio: "1:1", duration_seconds: 45, scenes: 6 },
  { id: 7, slug: "recap-monthly", name: "月度回顾 · 90 秒", category: "marketing", aspect_ratio: "16:9", duration_seconds: 90, scenes: 4 },
  { id: 8, slug: "press-quote", name: "媒体引用 · 20 秒", category: "social", aspect_ratio: "9:16", duration_seconds: 20, scenes: 5 },
];

const QUEUE_FALLBACK: RenderTask[] = [
  { id: 901, project: "春季产品发布 — 智能腕环", priority: "rush", status: "running", progress: 0.62, eta_seconds: 64, worker: "gpu-cluster-3" },
  { id: 902, project: "AI Copilot · 60 秒产品演示", priority: "high", status: "running", progress: 0.31, eta_seconds: 142, worker: "gpu-cluster-1" },
  { id: 903, project: "入职培训 · 销售工程师训练营", priority: "normal", status: "queued", progress: 0, eta_seconds: 612, worker: null },
  { id: 904, project: "媒体引用 · C 轮发布", priority: "normal", status: "queued", progress: 0, eta_seconds: 740, worker: null },
  { id: 905, project: "合规培训 — GDPR 要点", priority: "low", status: "queued", progress: 0, eta_seconds: 1340, worker: null },
];

const BRAND_KIT_FALLBACK: BrandKit[] = [
  {
    id: 1,
    name: "Acme · 核心版",
    primary_color: "#0F2A4A",
    accent_color: "#22D3B7",
    font_heading: "Inter Display",
    font_body: "Inter",
    voice: "alloy-en-female",
    tone: {
      voice_profile: "自信、平实、不夸张",
      do: ["先讲客户得到了什么", "用单音节动词", "屏幕上每句话不超过 14 字"],
      avoid: ["行业黑话", "陈词滥调", "感叹号"],
    },
  },
  {
    id: 2,
    name: "Acme · 线下活动",
    primary_color: "#101728",
    accent_color: "#FF7849",
    font_heading: "Inter Display",
    font_body: "Inter",
    voice: "ember-en-male",
    tone: {
      voice_profile: "温暖、像主持人在聊天",
      do: ["先点出城市", "用一个问题开场"],
      avoid: ["千篇一律的活动套话"],
    },
  },
];

const ANALYTICS_FALLBACK: Analytics = {
  kpis: [
    { label: "本月渲染次数", value: 387, delta: 0.124, unit: "videos" },
    { label: "首版成片平均耗时", value: 4.8, delta: -0.31, unit: "minutes" },
    { label: "一次审核通过率", value: 0.92, delta: 0.06, unit: "ratio" },
    { label: "较外包代理节省", value: 168_400, delta: 0.21, unit: "usd" },
  ],
  timeseries: [
    { day: "周一", rendered: 42, approved: 38, rejected: 4 },
    { day: "周二", rendered: 51, approved: 47, rejected: 4 },
    { day: "周三", rendered: 49, approved: 46, rejected: 3 },
    { day: "周四", rendered: 63, approved: 60, rejected: 3 },
    { day: "周五", rendered: 74, approved: 67, rejected: 7 },
    { day: "周六", rendered: 48, approved: 45, rejected: 3 },
    { day: "周日", rendered: 60, approved: 55, rejected: 5 },
  ],
  distribution: [
    { label: "营销", value: 41 },
    { label: "培训", value: 24 },
    { label: "产品演示", value: 19 },
    { label: "社交", value: 16 },
  ],
};
