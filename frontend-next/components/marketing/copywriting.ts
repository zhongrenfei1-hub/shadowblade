/**
 * ShadowBlade · 文案常量集
 *
 * 规则（严格执行）：
 * - 简体中文，简洁、专业、不夸张
 * - 不要：「赋能」「抓手」「闭环」「链路」「打通」「一站式」「极致」
 * - 不要感叹号
 * - 不要「您」（用「你」，SaaS 风格）
 * - 短句优先，14 字内最佳
 *
 * 修改前请同步 `docs/next-showcase-001.md` 的语态备注。
 */

/* ------------------------------------------------------------------ */
/*  首页主标候选 — HERO_LINES                                          */
/* ------------------------------------------------------------------ */

/**
 * 首页主标候选（landing hero headline）。每句 ≤ 18 字。
 *
 * 选用建议：
 * - 默认走 `HERO_LINES[0]`（与现有 OG / 静态站对齐）。
 * - A/B 测试时优先 [0]、[2]、[4] —— 三句的节奏与押韵差异最大。
 * - 培训 / 内训客户优先 [3]；社交内容团队优先 [5]。
 */
export const HERO_LINES = [
  "从简报到成片，只需 4 分钟。",
  "把视频生产搬进流水线。",
  "一份简报，就能跑完整条流水线。",
  "让每个团队都能稳定出片。",
  "品牌一致的视频，按周交付。",
  "脚本、配音、合成、渲染，一次跑完。",
] as const;

/* ------------------------------------------------------------------ */
/*  按钮文案 — CTA_LABELS                                             */
/* ------------------------------------------------------------------ */

/**
 * 12 条常用 CTA 文案。命名采用 `场景_动作` 的 SCREAMING_SNAKE_CASE，
 * 便于在 Storybook / 复盘里检索。
 */
export const CTA_LABELS = {
  /** 工作台 / 编辑器的主要 CTA */
  CREATE_VIDEO: "一键生成视频",
  /** 营销首页主 CTA */
  GET_STARTED: "立即开始",
  /** 营销首页副 CTA */
  WATCH_DEMO: "观看演示",
  /** 已登录用户回到工作台 */
  OPEN_WORKSPACE: "进入工作台",
  /** 项目列表新建按钮 */
  NEW_PROJECT: "新建项目",
  /** 素材库上传 */
  UPLOAD_ASSET: "上传素材",
  /** 团队页邀请成员 */
  INVITE_MEMBER: "邀请成员",
  /** 品牌套件新增 */
  ADD_BRAND_KIT: "新增品牌套件",
  /** 渲染队列重试 */
  RETRY_RENDER: "重新渲染",
  /** 销售联系 / 试用申请 */
  CONTACT_SALES: "联系销售",
  /** 文档 / 帮助中心 */
  READ_DOCS: "查看文档",
  /** 通用：批准 / 通过审核 */
  APPROVE: "批准",
} as const;

export type CtaKey = keyof typeof CTA_LABELS;

/* ------------------------------------------------------------------ */
/*  空状态文案 — EMPTY_STATES                                          */
/* ------------------------------------------------------------------ */

export interface EmptyStateCopy {
  /** 标题，14 字内 */
  title: string;
  /** 描述，一句话，说明下一步可以做什么 */
  description: string;
  /** 主 CTA 文案。语态与 `CTA_LABELS` 一致 */
  action_label: string;
}

/**
 * 8 个常见空状态文案。按 SaaS 高频场景编排。
 *
 * key 命名：`no_<entity>` 单数；与 `<EmptyState>` 一一对应。
 */
export const EMPTY_STATES = {
  no_projects: {
    title: "还没有项目",
    description: "新建一个项目，把简报变成第一条成片。",
    action_label: "新建项目",
  },
  no_assets: {
    title: "素材库是空的",
    description: "上传 logo、口播底、空镜素材，团队就能复用。",
    action_label: "上传素材",
  },
  no_approvals: {
    title: "审批都处理完了",
    description: "新视频提交审核时，会在这里通知你。",
    action_label: "回到工作台",
  },
  no_team_members: {
    title: "还没有团队成员",
    description: "邀请同事加入，分配角色和渲染配额。",
    action_label: "邀请成员",
  },
  no_comments: {
    title: "还没有评论",
    description: "在审阅界面圈出问题，团队会收到通知。",
    action_label: "打开审阅",
  },
  no_renders: {
    title: "渲染队列已清空",
    description: "队列空闲也算正常，下一条任务会自动排进来。",
    action_label: "查看历史任务",
  },
  no_brand_kits: {
    title: "还没有品牌套件",
    description: "新增一套品牌色、字体和 logo，渲染时会自动套用。",
    action_label: "新增品牌套件",
  },
  no_webhooks: {
    title: "还没有 Webhook",
    description: "添加一个端点，把渲染状态推送到你的系统。",
    action_label: "新增 Webhook",
  },
} as const satisfies Record<string, EmptyStateCopy>;

export type EmptyStateKey = keyof typeof EMPTY_STATES;
