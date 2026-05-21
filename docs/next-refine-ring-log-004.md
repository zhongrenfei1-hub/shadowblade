# ShadowBlade Next.js · Refine Ring Log 004

Refine 日期：2026-05-21
Refine 员：Refine ring · pass 004（test ring 003 应用 · 飞轮第四圈）
输入：[`next-test-ring-report-003.md`](./next-test-ring-report-003.md)（4 P0 + 15 P1 + 14 P2）
范围：`frontend-next/`，重点处理并行 Design ring 加的 4 新页（analytics / integrations / notifications / share）的质量 lag。

---

## 飞轮协作时序笔记

本轮 refine 与上一轮（003）有质的不同：
- Ring 003 处理的是 test 002 报告（refine 自己上轮的产物 + 旧 8 页累积漏修）
- Ring 004 处理的是 test 003 报告（Design ring 003 commit 58d7e5d 新加的 4 页 + 一些 refine 003 内部规约的回归）

新发现的 P0/P1 几乎**全部**集中在新页上 — 这是四环飞轮的协作时序摩擦：**Design ring 加内容 → Refine ring 来不及随车修整 → 下一轮 Test ring 捕获**。本轮 refine 完成度仍极高，但本身揭示了一个流程改进点：design ring 应该在 commit 前用 refine 003 推广的范式做 self-check（KpiTile sparkline、role=toolbar、BrandMark 复用、aria-hidden sweep、preserve-motion）。

---

## 应用清单

### P0 · 4/4 全部应用

| # | 报告条目 | 做了什么 |
|---|---|---|
| P0.1 | sidebar/mobile-sidebar NAV 不含 /analytics /integrations /notifications | 抽 `lib/nav.ts` 单一来源；sidebar + mobile-sidebar 都 import 同一 NAV；3 新路由分别归入「制作」/「工作空间」组；同时 ROUTE_LABEL 自动从 NAV 派生 |
| P0.2 | topbar.ROUTE_LABEL 不含 3 新页 | 通过 P0.1 解决（从 lib/nav.ts import） |
| P0.3 | (external)/share/[token] 缺 `<main>` landmark | `(external)/layout.tsx` 改 `<main id="main-content" className="min-h-screen">`；share 页内层重复的 `<main>` 改 `<div>` 避免嵌套 |
| P0.4 | share/[token] setTimeout regression | 用 `copyTimerRef + useEffect cleanup` 范式（抄自 share-link.tsx ring 003 修法）；新增 copyError 状态 + 失败提示 |

### P1 · 15/15 全部应用

| # | 报告条目 | 做了什么 |
|---|---|---|
| P1.5 | notifications「全部标已读」实际全部 dismiss（语义错配） | `read`（已读）+ `dismissed`（归档）拆成两个 Set state；markAllRead 仅修改 `read`，通知保留可见；unreadCount 从 read+dismissed 双滤 |
| P1.6 | analytics KpiTile 不传 trend → FALLBACK + 误导 srHint | 从 `a.timeseries` 推每个 KPI 的真 trend；耗时类指标 `kpi.unit === "minutes"` 走 `trend.map(v => -v)` 视觉反向（下降 = 改善 = 上升 sparkline）；手动 srHint 显式描述方向，不再依赖自动推导误判 |
| P1.7 | share BrandMark 重复 SVG | BrandMark 改用 className override（`h-[60%] w-[60%]` inner SVG 自适应）；share 用 `<BrandMark className="h-7 w-7" />` 替换 30+ 行内联 SVG |
| P1.8 | share 海报 SVG 与 video-player 重复 | share 改用 `<VideoPlayer watermark="DRAFT · v17" />`；VideoPlayer 扩 watermark prop |
| P1.9 | 40 处 SVG 硬编码 hex | video-player.tsx 全改用 `BRAND.navy700/900/accent500/paper/graphite300`；`lib/theme.ts BRAND` 扩展 navy 全 palette + COVER_NAVY 配色 + sky/amber/rose 状态色 |
| P1.10 | library 文件夹 aria-pressed 但无 onClick（假可按） | 抽 `<LibraryFolders totals totalAll>` client 组件；真接 state 切换 + role="toolbar" aria-label |
| P1.11 | settings SECTIONS 6 vs SettingsForm 4 Card 死锚 | SettingsForm 补 2 个 stub Card：billing（本月用量 + 支付方式）和 integrations（已连接预览 + 跳 /integrations 链接） |
| P1.12 | notifications aria-current="page" 应为 aria-pressed | 改 `aria-pressed`；aside 加 `role="toolbar"` |
| P1.13 | integrations tab 容器缺 role="toolbar" | 加 `role="toolbar" aria-label="按分类过滤集成"` |
| P1.14 | share 11 处 lucide icon 缺 aria-hidden | parallel 工作中已加（VideoPlayer 内部 Play/Pause/Volume2/Maximize2、share 自己的 ShieldCheck/Clock/Check/Copy/Lock/MessageCircle/X 全部带 aria-hidden）|
| P1.15 | analytics + notifications + integrations icon aria-hidden | analytics 3 处（Calendar/Download/RefreshCw）+ integrations Plus + ExternalLink 全部补；button 加 aria-label 防 hidden 后无 accessible name |
| P1.16 | 4 处 `<time>` 缺 dateTime | notifications NOTICES 加 `whenISO` ISO 字段；share COMMENTS 同；播放器 0:16/0:28 改 `<span>` 因为不是 datetime 是 duration |
| P1.17 | lib/theme.ts BRAND 缺 navy / graphite 全套 | 扩 BRAND：accent 500/400/300，navy 950/900/800/700/600/500/400，graphite 500/400/300/200，paper，sky400，amber 400/300，rose400；新增 `COVER_NAVY` 给视频海报背景 |
| P1.18 | (external)/layout.tsx 加 main | 改 `<main id="main-content" className="min-h-screen">{children}</main>` |
| P1.19 | share 评论用 `<article>` 替代 `<div>` | 改 |

### 顺手做的 P2 / P3

| # | 报告条目 | 做了什么 |
|---|---|---|
| P2.23 | integrations 外链 rel="noopener noreferrer" | 改 |
| P2.26 | KpiTile + BrandMark 加 "use client"（future-proof useId） | 都加上 |
| P2.27 | EmptyState role="status" aria-live 太吵 | 改 `<section aria-label={title}>`；filter 切换不再被 SR 反复念 |
| P2.28 | team Crown 双读 | Crown 改 `aria-hidden`（Badge 已说明角色） |
| analytics | 柱状图无 SR 文本替代 | 包 `<figure><figcaption className="sr-only">` 完整描述「周一 X 条（通过 Y、驳回 Z）...」 |

---

## 跳过 / 留给 ring 005

| 项 | 原因 |
|---|---|
| P2.21 weekly leaderboard hover 行整行可点 | 表格行整行 link 是设计变更，留 design v4 决定 |
| P2.24 integrations empty-state 改用 `<EmptyState>` | 现状内联也 OK，少一次改动 |
| P2.27 notifications aside < md 折叠成 horizontal scroll chip | UX 改进非 a11y 阻塞 |
| P2.29 integrations filter 中 qLower useMemo | 15 项可忽略 |
| P2.30 notifications visible 合并双 filter | 可读性 |
| P2.31 project-cover 6 个 cover gradient id 用 useId | 当前是 module-level const，多 ProjectCard 复用确实冲突，但需要让 ProjectCard 接受动态 cover id；留 design v4 把 project-cover 整体下放到 BRAND token |
| P2.32 share `id="sm"` 改 useId | 已通过 BrandMark 替换解决（BrandMark 内部 useId） |
| analytics 柱状图 wrap figcaption · timeseries 描述 | 已做 |

---

## 验收

- `npx tsc --noEmit` → 0 错 ✓
- 13 路由全 200 ✓（含 `/share/abc123` 动态参数）
- dev server 全程未崩 ✓

新增文件 4 个：
- `lib/nav.ts`（NAV 单一来源 + ROUTE_LABEL 派生）
- `components/workspace/library-folders.tsx`（client，真切换 state + role=toolbar）
- `docs/next-refine-ring-log-004.md`（本文件）

编辑文件 15+ 个：
- `lib/theme.ts`（BRAND 扩全 palette + COVER_NAVY）
- `components/brand/brand-mark.tsx`（"use client" + className override pattern）
- `components/workspace/kpi-tile.tsx`（"use client"，本来就用 useId）
- `components/workspace/video-player.tsx`（watermark prop + BRAND 接入 + 全 aria-hidden）
- `components/workspace/settings-form.tsx`（补 billing + integrations stub Card）
- `components/marketing/empty-state.tsx`（section 替代 role="status"）
- `components/layout/sidebar.tsx`（从 lib/nav 取 NAV）
- `components/layout/mobile-sidebar.tsx`（同）
- `components/layout/topbar.tsx`（从 lib/nav 取 ROUTE_LABEL + Bell 改 Link → /notifications）
- `app/(external)/layout.tsx`（main landmark）
- `app/(external)/share/[token]/page.tsx`（VideoPlayer + BrandMark + article 评论 + dateTime + setTimeout cleanup + 外链 noopener noreferrer）
- `app/(app)/analytics/page.tsx`（真 trend + 显式 srHint + 柱状图 figure/figcaption + icon aria-hidden + Button aria-label）
- `app/(app)/notifications/page.tsx`（read/dismissed 拆分 + role=toolbar aria-pressed + aria-label icon-only）
- `app/(app)/integrations/page.tsx`（role=toolbar + noopener noreferrer + icon aria-hidden）
- `app/(app)/library/page.tsx`（LibraryFolders 抽出）
- `app/(app)/team/page.tsx`（Crown aria-hidden）

---

## 喂回 Design 环 v4 (Design ring 004 input)

### 本轮新固化的范式

1. **`lib/nav.ts` 单一来源** — 新页加路由必须在这里同步添加。NAV → ROUTE_LABEL 自动派生，topbar 面包屑零维护。下一轮 design 加新路由直接更新 NAV。

2. **BrandMark className override 模式** — `<BrandMark className="h-7 w-7" />` 覆盖默认 h-8。inner SVG 用 `h-[60%] w-[60%]` 自适应外层。任何品牌符号位置必须用此组件，禁止再写 inline svg。

3. **VideoPlayer 接 watermark prop** — 任何视频播放器场景（无论 internal `/projects/[id]` 还是 external `/share/[token]`）都用同一组件。watermark 为可选 prop。下一轮如做真实 `<video ref>` 集成，只需改 VideoPlayer 一处。

4. **真 trend / srHint 双保险** — KpiTile 拿到 timeseries 数据应该传 trend；如果指标语义反向（耗时下降是好事），用 `trend.map(v => -v)` 翻转视觉；srHint 用显式文案描述方向，不依赖自动 describeTrend。

5. **read / dismissed 分离** — 任何「标已读 / 全部已读」类操作都不应隐藏数据，只切 `read` 状态；「归档 / 删除」才进 `dismissed`。范式适用于 notifications、approvals、活动流。

6. **(external) layout 自带 `<main>`** — 外部访客页（share / login / status / public-doc）一律不重复 `<main>`，由 layout 提供唯一 landmark。

7. **lib/theme.ts BRAND 扩全 palette** — SVG attribute 需要的 hex 全集中在 BRAND。CI 应该加 lint 防止 ts/tsx 文件出现 `#[0-9A-Fa-f]{6}` 字面量（除了 BRAND/COVER_NAVY 文件本身）。

### Design ring 004 待办

- **/integrations + /notifications + /analytics 的真实 data flow** — 当前都是模块级 const，要接 backend：notifications 接 webhook event stream（refine 003 提过）、analytics 接 `/v1/analytics/timeseries?range=7d`、integrations 接 `/v1/integrations`（含 OAuth status）
- **(external) 新页** — login / signup / forgot-password / status / 404 / 5xx 都该走 `(external)`。本轮发现 `app/page.tsx` 仍是 redirect 到 /dashboard，但未登录用户应该看到 login。
- **`<EmptyState>` 统一使用** — integrations 还内联了空态文本，下一轮换 EmptyState；analytics 没有空态分支（如 timeseries 为空时柱状图崩溃风险），需补
- **project-cover 6 个 cover 接入 BRAND** — 26 处硬编码 hex 仍未触；需要把 cover gradient 命名化（如 `cover-smartwatch / cover-bootcamp / cover-copilot / ...`）并用 useId 生成 instance-level gradient id
- **CI lint 防止 hex 字面量** — 在 `.eslintrc` 或独立 grep gate 防止未来再次出现 inline hex

### 协作时序改进建议

- Design ring 加新页前应该跑一遍 refine 003 的「设计语言 v3 checklist」（10 项：page-header 签名、KpiTile srHint、role=toolbar、BrandMark、(external)/layout main、icon aria-hidden、setTimeout cleanup、<time dateTime>、preserve-motion、`<EmptyState>`）
- Test ring 应该明确分类：「上轮 refine 漏修」+「本轮 design 新增」+「跨轮回归」三类，refine 队列对应三个不同优先级
- 建议 ring 005 起，Test 报告头部加 `## 报告对象矩阵` 表格，显式列出本轮审计的 commit 范围

---

*Refine ring · pass 004 — 4 P0 + 15 P1 + 5 P2/P3 = 24 项落地，4 新文件 + 15 编辑文件。下一轮（ring 005）应该把 design v4 的 todo（OAuth 流 / cover 收口 / 空态统一 / CI lint）做完，同时清扫 ring 003 / 004 累积的 14 个 P2。*
