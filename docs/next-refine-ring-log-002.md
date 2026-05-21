# ShadowBlade Next.js · Refine Ring Log 002

Refine 日期：2026-05-21
Refine 员：Refine ring · pass 002（vibe-Bug 修复轮）
范围：`frontend-next/`
输入：Test ring 003/004 提到的 P0/P1/P2 vibe-Bug + 六维 vibe-quality（操作流畅度 / 专业信任感 / 按钮反馈 / 数据面板清晰度 / 团队协作体验 / 移动端友好）

---

## 总览

本轮聚焦「vibe」——不是 a11y / 类型错误，而是「看着像不像企业级 SaaS」「按下去有没有反馈」「在 360px 屏上是不是一坨」。

### 六维优化清单

| # | 维度 | 落地 |
|---|---|---|
| 1 | 按钮反馈 + 微交互 | `Button` cva 增加 `active:scale-[0.97] active:duration-75` + `active:translate-y-0` + 不同 variant 的 active shadow；`Tabs` active 加渐变背景 + inset ring；`Input` / `Textarea` focus 加 accent halo（3px ring）+ bg 微提亮。effect 是「点哪儿都有声音」。 |
| 2 | 数据面板清晰度 | `KpiTile` 全量重写：左数右迷你 sparkline（动态 SVG，从最小 / 最大值映射），数字加大、suffix 弱化；新增 `trend?: number[]` prop，dashboard / team 全部 KPI 喂上 7 个数据点。`PipelineStage` running 态加 inline progress bar + shimmer 流光 + sky 描边 + 「运行中」标签。 |
| 3 | 专业信任感 | `Card` 加 inset highlight `0 1px 0 rgba(255,255,255,.04) inset` + `0 12px 32px -20px rgba(0,0,0,.45)` 的低位投影；`StatusBadge` 给 rendering / scripting / storyboard 加 `animate-pulse-ring`（呼吸光晕），其它状态固定 dot；`globals.css` 增 `hairline` utility、`prefers-reduced-motion` guard、`dot-online/idle` 状态点伪元素。Topbar 加 backdrop-blur-xl + 通知红点（"3"）。 |
| 4 | 操作流畅度 | `CreateWizard` 大改：① localStorage 草稿 autosave + 恢复提示（顶部 banner，3.5 秒后自动收起）② 流水线运行中可 cancel ③ 错误态 alert（rose 配色 + 重试按钮）④ 完成态 success（accent pulse-ring + 查看成片 CTA）⑤ 模板卡选中加 ✓ 角标 + selected shadow ⑥ 简报字数实时计数。`app/loading.tsx` 从单 spinner 换成全页 skeleton（hero + 4 KPI + 2 column cards）。 |
| 5 | 团队协作体验 | `lib/api.ts` Workspace.team 扩 `email / presence / last_active` 三个可选字段，fallback 全部填上真实邮箱（不再从 name 推导，解决 ring 001 跳过的 P2.27）；team 页双视图（< md 卡片，≥ md 表格）、avatar 右下 presence dot（online 加 accent glow，idle amber，offline 灰）、新增「最近动作」列（"刚刚批准 v17 渲染"）、管理员用 `Crown` icon 标识；`MetaTabs` 评论卡片加 thread 计数徽章、presence dot、scope-cite 加 accent 圆点；composer 加字数计数 + ⌘+Enter 提示 + 发送 loading 态。 |
| 6 | 移动端友好 | 新增 `components/layout/mobile-sidebar.tsx`：280px 抽屉，backdrop blur + Esc 关闭 + 路由切换自动关；topbar 增 hamburger trigger（< md 显示）+ 路由切换关抽屉的 effect。dashboard / projects / project-detail / templates / library / brand / settings / team 共 8 个页头统一 `flex flex-wrap items-end gap-4`（< md 不再 6 列挤一行）、h1 从固定 34px → `text-[28px] md:text-[34px]`、CTA 文案 < sm 折叠为短词或纯 icon。team 表 < md 走卡片视图，分类筛选 button 加 count 徽章。 |

---

## 顺手补的几件事

1. **dashboard 类别 tab 变可用** —— 抽 `ProjectFilter` client 组件（test ring 001 P2.18），按 purpose 过滤 + 实时 count + 空态文案。
2. **projects 页 hardcode count 替换** —— 抽 `ProjectsBoard` client 组件，从 `total` 取「全部」、按 purpose 聚合各分类、加状态 / 负责人 select（test ring 001 P1.16 + P2.16）。
3. **dashboard "!" 字符** —— 换 `AlertTriangle` icon + amber border（test ring 001 P2，ring 001 跳过的）。
4. **fade-up 进入动画** —— ProjectCard / 提示 banner / success alert 全用，加 `prefers-reduced-motion` 守护避免晕动症投诉。
5. **每个 page 的 sticky topbar 锚定行为** —— 不动；topbar 已经 `sticky top-0` ，z-20 抬高一档避免 drawer 覆盖问题（drawer z-50）。

---

## 跳过 / 留给 ring 003

| 项 | 原因 |
|---|---|
| 视频播放器真实 `<video>` 接入 | 仍是占位，需要拿到 MP4 资产，留接 backend `/projects/:id/render_url` 时一起 |
| audit-log / analytics 等 frontend/ (旧 HTML) 同步翻新 | 本轮 scope 限 frontend-next/；旧 HTML 等 ring 003 |
| 富文本评论 / 真实 @ 提及补全 | composer 还是纯 textarea，需要接 mentions API |
| 真实在线状态（websocket / presence service） | presence 仍是 fixtures 字段，留给后端 |
| 整体 motion token（duration / easing 抽到 tailwind config） | 当前 hardcode 在 cva 里，跨轮统一 |
| Sidebar 抽屉的 focus trap | drawer 已 Esc 关闭 + 点遮罩关闭，focus trap 留下一轮 |

---

## 文件触动

新增：
- `components/layout/mobile-sidebar.tsx`
- `components/workspace/project-filter.tsx`
- `components/workspace/projects-board.tsx`
- `docs/next-refine-ring-log-002.md`（本文件）

编辑：
- `app/globals.css`（utilities + keyframes + reduced-motion）
- `app/loading.tsx`（→ skeleton）
- `app/dashboard/page.tsx`
- `app/projects/page.tsx`
- `app/projects/[id]/page.tsx`
- `app/team/page.tsx`
- `app/templates/page.tsx`
- `app/library/page.tsx`
- `app/brand/page.tsx`
- `app/settings/page.tsx`
- `components/ui/button.tsx`
- `components/ui/card.tsx`
- `components/ui/input.tsx`
- `components/ui/textarea.tsx`
- `components/ui/tabs.tsx`
- `components/workspace/kpi-tile.tsx`
- `components/workspace/pipeline-stage.tsx`
- `components/workspace/status-badge.tsx`
- `components/workspace/create-wizard.tsx`
- `components/workspace/meta-tabs.tsx`
- `components/layout/topbar.tsx`
- `components/layout/sidebar.tsx`
- `lib/api.ts`（Workspace.team 扩字段）

---

## 验收

- `npx tsc --noEmit` → 0 error ✓
- 9 个路由（`/dashboard /create /projects /projects/101 /templates /library /brand /team /settings`）全部 200 ✓
- dev server 全程未崩 ✓

---

## 喂回 Design 环 (Design ring 002 input)

下一轮 Design 应该把本轮的 token / 组件 / 交互范式正式收编为「设计语言 v2」，并在新页面里默认使用：

### 新设计 token（写进 `tailwind.config.ts` 或 css var）

- `--motion-bounce: 150ms ease-out` —— 按钮 / hover 标准
- `--motion-snap: 75ms ease-out` —— active scale 标准
- `--shadow-card: 0 1px 0 0 rgba(255,255,255,0.04) inset, 0 12px 32px -20px rgba(0,0,0,0.45)` —— 所有 Card
- `--ring-focus: 0 0 0 3px rgba(34,211,183,0.25)` —— Input / Textarea / Select / 搜索框 focus
- `--dot-online`, `--dot-idle`, `--dot-offline` —— 协作状态点
- `--pulse-ring-accent` keyframe —— 状态徽章呼吸光

### 新组件 / 交互范式

1. **KpiTile 必带 sparkline** —— 后续所有数据面板默认带 7 点 trend，无 trend 数据时用 `[4,6,5,7,8,7,9]` 占位（已内置）。Design 拿到 analytics fixtures 后填真实历史。
2. **PipelineStage running 必带 inline progress** —— 任何"step in progress"展示都该有 progress bar + shimmer。
3. **Mobile-first 抽屉** —— 新页面如果有 sidebar，默认 `< md` 走 mobile-sidebar drawer。topbar 自带 hamburger trigger。
4. **草稿 autosave 习惯** —— 任何长表单（create / settings / brand 编辑 / new-webhook）都该 localStorage 自动保存 + 恢复提示。
5. **协作 presence 三态** —— team / 评论 / approval 列表的 avatar 默认带 dot。
6. **页头响应式范式** —— h1 `text-[28px] md:text-[34px]` + CTA `<span className="hidden sm:inline">` + 容器 `flex flex-wrap items-end gap-4 md:gap-6` 是统一签名。

### 需要 Design 接续设计的新场景

- **空态插画** —— ProjectFilter / ProjectsBoard / library 各种过滤后无结果，目前是 dashed border + 一行文字。Design 应给 EmptyState 模式补轻量插画（`/showcase/screens/screen-empty-*.svg`）。
- **协作面板** —— team 页右上还差「在线 5 人 头像堆」"presence stack"组件，可以借鉴 Figma / Notion 头像堆叠。
- **失败恢复 UX** —— create-wizard 的错误重试目前 inline alert + 重试按钮；Design 应思考一份「错误页面 / 错误 drawer / inline 重试」三段式范式。
- **微交互节奏** —— 按钮、卡片、tab、入场都已有动画，但目前各自有节奏。Design 应定一份"motion grammar"（duration ladder: 75 / 150 / 250 / 400）。
- **暗色 + 玻璃感平衡** —— 当前 backdrop-blur 用在 topbar / sidebar / drawer overlay，Card 没用 blur；评估是否给 modal / dropdown 加 blur。

---

*Refine ring · pass 002 — 6 维 vibe-quality + 3 个顺手 P2，21 个文件触动。下一轮（ring 003）应该让 Design 把上述设计语言 v2 落地到新的工作流页面（webhook-flow / brand-diff / asset-detail），并把旧 frontend/HTML 同步对齐。*
