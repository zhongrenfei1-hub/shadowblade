# Next.js Showcase ring · pass 001

> 强化 ShadowBlade Next.js 前端的品牌叙事和文案质感。本次只新增文件，不动 Design 环已交付的 page / shell / ui / workspace / lib。

## 交付清单

| 类别 | 文件 | 说明 |
| --- | --- | --- |
| 组件 | `frontend-next/components/marketing/empty-state.tsx` | 通用 `<EmptyState>` 组件，accent-cyan 圆环图标 + 标题 + 描述 + CTA |
| 组件 | `frontend-next/components/marketing/hero-illustration.tsx` | 工作台 / 营销页面用的流水线大插图（React JSX + Tailwind token） |
| 文案 | `frontend-next/components/marketing/copywriting.ts` | `HERO_LINES`、`CTA_LABELS`、`EMPTY_STATES` 三组常量 + 类型 |
| 视觉 | `frontend-next/public/og-image.svg` | 1200×630 OG 卡片，"ShadowBlade · 4 分钟出片" |
| 视觉 | `frontend-next/public/favicon.svg` | 32×32 品牌 mark，沿用 SB 闪电图形 + accent 渐变 |
| 文档 | `docs/next-showcase-001.md` | 本文件 |

## 文案语态备注

写作规则统一遵循 `docs/i18n-glossary.md` + 本任务的硬约束：
- 简体中文、简洁、专业、不夸张
- 不用「赋能」「抓手」「闭环」「链路」「打通」「一站式」「极致」
- 不用感叹号；不用「您」（用「你」）
- 短句优先，14 字内最佳

### `HERO_LINES` · 6 句首页主标候选

| # | 文案 | 语态 / 适用场景 |
| --- | --- | --- |
| 0 | 从简报到成片，只需 4 分钟。 | 默认款。与现有 OG、`frontend/public` 静态版的承诺对齐。营销首页主推。 |
| 1 | 把视频生产搬进流水线。 | 工程师 / 平台买家偏好；强调"流水线"这一核心隐喻。 |
| 2 | 一份简报，就能跑完整条流水线。 | 描述性、动作清晰；适合中段段落标题或 hero 副标。 |
| 3 | 让每个团队都能稳定出片。 | 内训 / L&D 客户偏好；强调"稳定 + 团队复制"。 |
| 4 | 品牌一致的视频，按周交付。 | 品牌负责人、CMO 视角；隐含交付节奏。 |
| 5 | 脚本、配音、合成、渲染，一次跑完。 | 罗列型，让买家看到完整工序；适合解释段落开头。 |

> 选用建议：A/B 测试优先 `[0]`、`[2]`、`[4]` —— 节奏与押韵差异最大；其余作为不同 audience landing 的备选。

### `CTA_LABELS` · 12 条按钮文案

| Key | 文案 | 适用 |
| --- | --- | --- |
| `CREATE_VIDEO` | 一键生成视频 | 工作台 / 编辑器主 CTA（与 dashboard 现有按钮一致） |
| `GET_STARTED` | 立即开始 | 营销页主 CTA |
| `WATCH_DEMO` | 观看演示 | 营销页副 CTA |
| `OPEN_WORKSPACE` | 进入工作台 | 已登录用户 |
| `NEW_PROJECT` | 新建项目 | 项目列表 / 空状态 |
| `UPLOAD_ASSET` | 上传素材 | 素材库 / 空状态 |
| `INVITE_MEMBER` | 邀请成员 | 团队页 |
| `ADD_BRAND_KIT` | 新增品牌套件 | 品牌套件页 |
| `RETRY_RENDER` | 重新渲染 | 渲染失败行的行内按钮 |
| `CONTACT_SALES` | 联系销售 | 企业版价格 / 高 ARR 入口 |
| `READ_DOCS` | 查看文档 | 帮助中心 / 开发者控制台 |
| `APPROVE` | 批准 | 审批列表行内（与 dashboard `APPROVALS` 一致） |

> 命名：`场景_动作` 的 SCREAMING_SNAKE_CASE，便于在 Storybook / 复盘里检索。

### `EMPTY_STATES` · 8 个空状态文案

每条都是 `{ title, description, action_label }`。

| Key | title | 语态备注 |
| --- | --- | --- |
| `no_projects` | 还没有项目 | 中性 + 邀请：「新建一个项目，把简报变成第一条成片」。 |
| `no_assets` | 素材库是空的 | 强调团队复用：「上传 logo、口播底、空镜素材，团队就能复用」。 |
| `no_approvals` | 审批都处理完了 | 正向反馈，避免「inbox zero」的英文行话；CTA 回到工作台。 |
| `no_team_members` | 还没有团队成员 | 直接描述事实；CTA 落在「邀请成员」。 |
| `no_comments` | 还没有评论 | 引导到审阅界面，避免「快来留下第一条评论」式的廉价语态。 |
| `no_renders` | 渲染队列已清空 | 安抚而非告警：「队列空闲也算正常，下一条任务会自动排进来」。 |
| `no_brand_kits` | 还没有品牌套件 | 强调好处：「渲染时会自动套用」。 |
| `no_webhooks` | 还没有 Webhook | 技术买家语态，避免感叹号；CTA 是「新增 Webhook」。 |

> 共同原则：title 必须 14 字内；description 一句话，告诉用户**下一步可以做什么**；不要解释「这个功能是干嘛的」。

## 组件使用约定

### `<EmptyState>`

```tsx
import { EmptyState } from "@/components/marketing/empty-state";
import { EMPTY_STATES, CTA_LABELS } from "@/components/marketing/copywriting";
import { FolderPlus } from "lucide-react";

<EmptyState
  icon={FolderPlus}
  {...EMPTY_STATES.no_projects}
  action={{ label: CTA_LABELS.NEW_PROJECT, href: "/create" }}
/>
```

- `action` / `secondaryAction` 都可选；任一存在就会渲染 CTA 行。
- 圆环图标的颜色固定为 `accent-cyan`；不要传 `className` 覆盖。
- 容器是 `Card`-likes 的 `bg-card/40` + `border` + `backdrop-blur`，可直接放在任何深色面板上。

### `<HeroIllustration>`

```tsx
import { HeroIllustration } from "@/components/marketing/hero-illustration";

<HeroIllustration className="mx-auto" label="ShadowBlade 工作台流水线示意" />
```

- 默认 `w-full max-w-[760px]`，aspect 锁定在 16:10。
- 所有颜色通过 Tailwind class 注入到 SVG 内 `class` 属性（`[&_.hf-bg]:fill-navy-950` 这种），换主题时只改 token 不动 SVG。

## 视觉文件

### `public/og-image.svg`

- 1200×630，纯 SVG，无远程字体。
- 主标 "ShadowBlade · 4 分钟出片" 占据左半幅，4 分钟应用 `og-text` 渐变（accent-cyan → sky）。
- 右半幅是流水线圆环 + ETA chip + 合成进度小卡，与 hero 视觉同步。
- 字体回退栈：`Inter Display, Inter, PingFang SC, system-ui, sans-serif`。

### `public/favicon.svg`

- 32×32，沿用 SB 闪电图形 + accent 渐变（`#22D3B7` → `#38BDF8`）。
- 已在 `app/layout.tsx` 通过 `icons: { icon: "/favicon.svg" }` 注册（无需改 page）。

## 给 Test / Refine 的交接备注

1. **页面接入**：本次不动 page。下一环可以选择性把 `EmptyState` 替换到 `app/projects`、`app/library`、`app/team`、`app/settings/webhooks` 等位置。文案直接从 `EMPTY_STATES[<key>]` 解构即可。
2. **OG 接入**：若需要每页独立 OG，可在 `app/<route>/page.tsx` 里 `export const metadata = { openGraph: { images: ["/og-image.svg"] } }`。当前 `app/layout.tsx` 没有声明 OG，可以在不动现有 metadata 的前提下追加一个根级 `openGraph`。
3. **A/B 测试**：`HERO_LINES` 共 6 句；如果做 landing A/B，建议先跑 `[0]` vs `[2]` —— 前者承诺时间，后者承诺工序，能拆出"卖速度"和"卖流程"两条用户心智。
4. **空状态插图**：本次没有把 `hero-illustration.tsx` 用进 `<EmptyState>`；如需"大插图 + 文案"的空状态，建议封装 `<EmptyHero illustration={<HeroIllustration />} title=… />` 这种 wrapper，而不是动现有 `EmptyState`。
5. **图标可访问性**：`EmptyState` 的圆环图标已设 `aria-hidden`，组件本身用 `role="status"` + `aria-live="polite"`，屏幕阅读器读出 title + description 即可；不要再单独给图标加 label。
6. **风险点**：`hero-illustration.tsx` 使用 Tailwind v3 的 arbitrary variant + descendant selector（`[&_.hf-bg]:fill-navy-950`）批量给 SVG 子元素上色。如果未来切到 Tailwind v4 / CSS Modules，需要把这部分迁移到 `<style>` 或 `className` 直接挂在子元素上。
