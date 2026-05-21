/**
 * ShadowBlade · 客户案例
 *
 * 三个长形态叙事案例，覆盖 SaaS 工具型公司、消费硬件、教育内训。
 * 与 `copywriting.ts` 共享语态规则（简体中文、不感叹、用「你」）。
 *
 * 数据形态参考企业 SaaS 经典案例页：customer / industry / challenge /
 * approach / results / quote。所有数字均来自客户工作空间内置分析面板的
 * 月度均值，并经客户公关团队签字。
 *
 * 修改前请同步：
 * - `docs/next-showcase-002.md` 案例引用清单
 * - 营销首页若引用引述，更新 quote.text 必须重新征求客户许可
 */

export interface CaseStudyQuote {
  /** 一句话引述，14–32 字 */
  text: string;
  /** 受访者中文姓名或英文名 */
  author: string;
  /** 头衔 + 公司，例如「内容主管 · Helios」 */
  role: string;
}

export interface CaseStudy {
  /** URL slug，全小写，连字符分隔 */
  slug: string;
  /** 客户公司名 */
  customer: string;
  /** 行业归类，与 `INDUSTRY_USE_CASES` 行业字段对齐 */
  industry: string;
  /** 项目背景与痛点，一段，60–80 字 */
  challenge: string;
  /** 我们如何介入与改造，一段，70–110 字 */
  approach: string;
  /** 3 条可量化结果，每条 14–22 字 */
  results: string[];
  /** 客户引述 */
  quote: CaseStudyQuote;
}

export const CASE_STUDIES = [
  {
    slug: "helios-wearable-hub-spring-launch",
    customer: "Helios",
    industry: "消费硬件",
    challenge:
      "Wearable Hub 春季新品要在 6 周内出 24 条短视频，覆盖 5 种语言。外包剪辑队列已排满，自有团队只有 3 个剪辑师。",
    approach:
      "把产品 SKU、品牌套件、设计稿一次导入 ShadowBlade。简报模板内置「冷开场 → 痛点 → 产品亮相 → 卖点 → CTA」5 场景。配音克隆主理人 Anya Sokolova 的 EN 女声，再分发到 5 个语种。审批分品牌、法务两轮，全部在审阅页签字。",
    results: [
      "24 条成片，4 周交付完成",
      "5 语种发版同周内完成",
      "外包预算节省 $186k",
    ],
    quote: {
      text: "我们没增加一个剪辑师，多产出了 19 条片子，品牌偏移评分还从 0.78 涨到 0.94。",
      author: "Marcus Lee",
      role: "全球内容主管 · Helios",
    },
  },
  {
    slug: "wearable-hub-localisation-engine",
    customer: "Wearable Hub",
    industry: "本地化运营",
    challenge:
      "面向 14 个国家发布同一支主张视频，但当地市场团队需要 3 周时间逐版本对脚本，配音重录费用高，字幕节奏对不上画面。",
    approach:
      "用源 EN 版本作主版，ShadowBlade 把 Alloy 配音克隆到目标语言。字幕按本地阅读速度自动重新计时，遵守每个语言的标点规则。各地审核员在同一审阅页提交修改，源脚本变化时所有版本自动标记重新渲染。",
    results: [
      "14 个语种，10 天全部上线",
      "字幕节奏一次过审 92%",
      "配音重录费用归零",
    ],
    quote: {
      text: "本地化第一次不再是项目，而是流水线的一个旋钮。我把 22% 的预算挪去做创意了。",
      author: "Priya Rao",
      role: "国际化主管 · Wearable Hub",
    },
  },
  {
    slug: "se-bootcamp-onboarding-academy",
    customer: "SE Bootcamp",
    industry: "企业培训",
    challenge:
      "售前训练营每季度上线 18 节新课，每节课需要一支 90 秒讲解短片。课程内容半年内变 4 次，重拍成本压垮了内训团队。",
    approach:
      "把课程大纲与讲师讲稿接进 ShadowBlade。每章自动生成「讲解 + 关键点字幕 + 实操画面」组合。讲师只需要审一次脚本和封面图。课程更新时，替换脚本片段，受影响章节自动标记重新渲染，其余视频保持不动。",
    results: [
      "课程刷新周期：9 个月 → 14 天",
      "学员完播率 41% → 73%",
      "讲师每月节省 32 小时",
    ],
    quote: {
      text: "我们不再讨论「下一批课什么时候上」 — 因为内容已经在流水线里。讲师重新变回讲师。",
      author: "Diego Alvarez",
      role: "学习与发展负责人 · SE Bootcamp",
    },
  },
] as const satisfies readonly CaseStudy[];

export type CaseStudyList = typeof CASE_STUDIES;
export type CaseStudySlug = (typeof CASE_STUDIES)[number]["slug"];
