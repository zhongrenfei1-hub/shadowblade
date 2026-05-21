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

/* ------------------------------------------------------------------ */
/*  企业版落地页 — ENTERPRISE_LANDING                                  */
/* ------------------------------------------------------------------ */

/**
 * 企业版落地页 6 个 section。
 *
 * 顺序：hero → trust → pipeline → governance → roi → cta
 * 与营销首页 `HERO_LINES` 共享语态，但更重「采购评审」「合规」「ROI」。
 *
 * 渲染建议：
 * - hero 用大字标 + 单按钮 CTA「联系销售」。
 * - trust 配合 SOC2 / GDPR / ISO 徽章。
 * - pipeline 6 步与 `PIPELINE_STEPS` 一一对应（脚本 / 分镜 / 配音 / 混剪 / 渲染 / 封面）。
 * - governance 高亮品牌套件、审批、审计日志。
 * - roi 三条数字 ROI，配 KPI 卡片。
 * - cta 双按钮：联系销售 + 看演示。
 */
export interface EnterpriseSection {
  /** 锚点 id，URL fragment 用 */
  id: string;
  /** 小标题（eyebrow），全大写、间距 0.16em 渲染 */
  eyebrow: string;
  /** 主标题，14 字内最佳，绝对不超过 26 字 */
  title: string;
  /** 段落正文，35 字内最佳 */
  body: string;
  /** 可选要点列表，每条 ≤ 14 字 */
  bullets?: string[];
}

export const ENTERPRISE_LANDING = {
  hero: {
    id: "hero",
    eyebrow: "ShadowBlade · 企业版",
    title: "把视频生产搬进流水线。",
    body: "一份简报，6 步流水线跑完。脚本、分镜、配音、混剪、渲染、封面 — 一次成稿，可追溯七年。",
    bullets: [
      "4 分钟出第一版",
      "品牌偏移自动拦截",
      "采购评审已就绪",
    ],
  },
  trust: {
    id: "trust",
    eyebrow: "安全与合规",
    title: "你的法务、安全、采购，都是用户。",
    body: "ShadowBlade 在你的租户内运行，密钥静态散列，配音克隆从不离开你的边界。",
    bullets: [
      "SOC 2 Type II 报告可下载",
      "ISO 27001 已认证",
      "GDPR · HIPAA · DPA 模板",
      "数据驻留 · EU · US · APAC",
      "审计日志保留 7 年",
    ],
  },
  pipeline: {
    id: "pipeline",
    eyebrow: "6 步流水线",
    title: "每一步都有名字、有耗时、有可重放的日志。",
    body: "从简报到上线封面，6 步统一记录。每条成片自动留存每一步耗时、模型、版本与人。",
    bullets: [
      "脚本 · 品牌语态评分 ≥ 0.9",
      "分镜 · 同主题视觉风格自动复用",
      "配音 · 克隆相似度可设阈值",
      "混剪 · 字幕逐词 · 安全区已内建",
      "渲染 · GPU 集群 · 99.97% SLA",
      "封面 · 主图 + A/B 候选自动出",
    ],
  },
  governance: {
    id: "governance",
    eyebrow: "治理与品控",
    title: "品牌套件是一等对象，不是样式表。",
    body: "色板、字体栈、安全区、法务声明 — 锁在套件里。审批通过前，偏移会被标记并自动修复。",
    bullets: [
      "品牌套件版本对比",
      "三级审批 · 创作者 / 品牌 / 法务",
      "审计日志按字段可查",
      "Webhook 投递 30 天可重放",
    ],
  },
  roi: {
    id: "roi",
    eyebrow: "可衡量的 ROI",
    title: "数字会说话。",
    body: "下面是 60 家企业客户在第一季度的均值表现。每个数字都来自工作空间内置的分析面板。",
    bullets: [
      "首版交付 4 分钟",
      "团队产能提速 68%",
      "外包预算节省 $184k/季",
    ],
  },
  cta: {
    id: "cta",
    eyebrow: "下一步",
    title: "用你自己的简报试一次。",
    body: "我们会在 24 小时内给你一份针对企业评估的样片，含安全问卷与定价模型。",
    bullets: [
      "联系销售 · 当日回复",
      "30 分钟产品演示",
      "免费试用 14 天",
    ],
  },
} as const satisfies Record<string, EnterpriseSection>;

export type EnterpriseSectionKey = keyof typeof ENTERPRISE_LANDING;

/* ------------------------------------------------------------------ */
/*  行业用例 — INDUSTRY_USE_CASES                                      */
/* ------------------------------------------------------------------ */

/**
 * 4 个行业典型用例：电商 / 金融 / 培训 / 政企。
 *
 * 渲染建议：4 列网格，每个卡片高度一致，metric 用作底部数字。
 */
export interface IndustryUseCase {
  /** 行业短名，URL slug 用 */
  industry: string;
  /** 主标题，≤ 16 字 */
  headline: string;
  /** 问题陈述，一句话，≤ 30 字 */
  problem: string;
  /** 解决路径，一句话，≤ 36 字 */
  solution: string;
  /** 关键指标，数字 + 单位 + 说明 */
  metric: string;
}

export const INDUSTRY_USE_CASES = [
  {
    industry: "电商",
    headline: "上新即上片。",
    problem: "每周上 80 个 SKU，外包剪辑等三天，错过首发节点。",
    solution: "把商品 CSV 接进流水线，按品牌套件批量出 30 秒短视频，提交审核当天上线。",
    metric: "出片提速 7×，CTR 提升 18%",
  },
  {
    industry: "金融",
    headline: "合规通过的产品视频。",
    problem: "理财、保险、信贷的成片必须三方过审，传统流程要 14 天。",
    solution: "在租户内运行，审计日志按字段留痕，合规、法务、市场在同一审阅页签字。",
    metric: "审批时长 14 天 → 38 小时",
  },
  {
    industry: "培训",
    headline: "课程内容自动出片。",
    problem: "L&D 团队有 200 节课大纲，没有制作人手，年初讲到 Q4 就过时。",
    solution: "课程大纲一次导入，按章节自动生成讲解短片，更新只需替换一条脚本。",
    metric: "课程刷新周期 9 个月 → 2 周",
  },
  {
    industry: "政企",
    headline: "数据驻留与可追溯。",
    problem: "政务、央企、医疗对数据驻留有强约束，公网 SaaS 难以进入采购清单。",
    solution: "私有部署 + 国密配音 + 自带审计日志，集成 SSO 与堡垒机访问。",
    metric: "通过 7 家央企采购合规评审",
  },
] as const satisfies readonly IndustryUseCase[];

export type IndustryUseCaseList = typeof INDUSTRY_USE_CASES;

/* ------------------------------------------------------------------ */
/*  异议处理 — OBJECTION_HANDLING                                      */
/* ------------------------------------------------------------------ */

/**
 * 销售对话中常见的 6 条异议 + 推荐回应。
 *
 * 用法：
 * - FAQ 页可直接渲染。
 * - 销售工程师在产品演示前可以用作话术蓝本。
 */
export interface Objection {
  /** 客户的原话或近义表达，≤ 18 字 */
  objection: string;
  /** 我们的标准回应，2 句以内，事实优先 */
  response: string;
}

export const OBJECTION_HANDLING = [
  {
    objection: "AI 视频看着不够专业。",
    response:
      "你不会拿 AI 默认风格直接发。每条成片对照你的品牌套件渲染，偏移会被拦截并自动修复，看上去就是你品牌的视频。",
  },
  {
    objection: "我们的品牌一致性怎么保。",
    response:
      "品牌套件是一等对象，色板、字体、安全区、法务声明锁在里面。任何偏移在审批前被标记，可一键回到合规状态。",
  },
  {
    objection: "数据合规怎么过。",
    response:
      "我们在你的租户内运行，配音克隆从不外发。SOC 2 Type II、ISO 27001、GDPR 都已就绪，采购评审材料可整包下载。",
  },
  {
    objection: "迁移成本太高了。",
    response:
      "无需迁移内容仓。把简报、品牌套件、现有素材接进流水线，14 天试用期内通常能跑出 3 条以上可发布成片。",
  },
  {
    objection: "团队学不会新工具。",
    response:
      "市场同事走简报路径，4 分钟出首版。剪辑师走编辑器路径，时间线和 Premiere 类似。我们的 NPS 是 58。",
  },
  {
    objection: "和我们现有工具会冲突吗。",
    response:
      "不会替换 Figma、Premiere、After Effects。我们补充的是「按周交付」的那一段：流水线 + 审批 + 渲染农场。",
  },
] as const satisfies readonly Objection[];

export type ObjectionList = typeof OBJECTION_HANDLING;
