# ShadowBlade Next.js · Refine Ring Log 003

Refine 日期：2026-05-21
Refine 员：Refine ring · pass 003（test ring 002 应用轮）
输入：[`next-test-ring-report-002.md`](./next-test-ring-report-002.md)（2 P0 + 15 P1 + 17 P2）
范围：`frontend-next/`（含本轮发现的 `app/(app)/` 路由组结构变化）

---

## 应用清单

### P0 · 2/2 全部应用

| # | 报告条目 | 做了什么 |
|---|---|---|
| P0.1 | `create-wizard.tsx` setInterval cleanup race | 删 `stepTimer` ref；`useEffect` 用局部 `const id`；`cancel()` 仅 `setRunning(false)` 让 cleanup 闭包接管。无双重 clearInterval、无窄窗口 race。 |
| P0.2 | `mobile-sidebar.tsx` 无 focus-trap / 无初始焦点管理 | 加 `dialogRef`；打开时移焦到第一个可聚焦元素、关闭时还焦给前一个 focused 元素；`Tab` / `Shift+Tab` 在 dialog 内循环（getFocusable 过滤 disabled / display:none），`Esc` 拦截 + preventDefault。 |

### P1 · 15/15 全部应用

| # | 报告条目 | 做了什么 |
|---|---|---|
| P1.3 | `shimmer` keyframe 双定义 | 删 tailwind.config 那份 keyframe，保留 globals.css；改 `pipeline-stage.tsx` 用 `animate-shimmer-slow` utility（在 tailwind extend animation 注册）。死代码 `animate-shimmer` 同时清掉。 |
| P1.4 | `JSON.parse(raw) as Draft` 不验证 | 新增 `safeParseDraft()` + `pickAllowed` / `pickString` helpers；ALLOWED_PURPOSES / ALLOWED_ASPECTS / ALLOWED_DURATIONS / ALLOWED_TEMPLATES / ALLOWED_VOICES 五个白名单；不合法值落 DEFAULT。`brief` 限长 2000 字、`cta` 限长 200 字。 |
| P1.5 | autosave race 首次 mount | 加 `initialMount: useRef(true)`，autosave effect 首次跳过；恢复 effect 同时清理 `restoredTimerRef`。 |
| P1.6 | `prefers-reduced-motion` 全局规则吃 `animate-spin` | 改 globals.css media query：`*:not(.preserve-motion):not(.preserve-motion *)` 排除特定层级；`PipelineStage` running Loader2、CreateWizard 大按钮 + 流水线列表 Loader2 都加 `preserve-motion`；同时给 `.animate-fade-up` reset 防眩晕。 |
| P1.7 | body overflow lock 副作用注释 | mobile-sidebar.tsx 加注释：每个 layer 各自 capture prev，链式安全。 |
| P1.8 | `app/(app)/create/page.tsx` 页头不响应式 | 改 `flex flex-wrap items-end gap-4 md:gap-6` + h1 `text-[26px] md:text-[34px]` + `min-w-0 flex-1`，对齐其它 8 页头签名。 |
| P1.9 | `KpiTile` id 冲突风险 | 用 `useId()` 替代 `kpi-grad-${label}`；同 label 多次复用不再撞 id。 |
| P1.10 | `library` FOLDERS hardcode count | 接 `api.assets().totals`；新增 `_total` 聚合（所有维度之和）；`totalBytes` 改从 items 累加；FOLDER_DEFS 改 `totalKey` 间接寻址；className 改 `cn()`。 |
| P1.11 | `templates` filter `i===0` 永远高亮 | 抽 `components/workspace/template-filter.tsx`（client），支持 5 个分类 + 实时 count + 空态文案 + fade-up 入场。 |
| P1.12 | `settings` 侧栏 `i===0` 永远高亮 | 抽 `components/workspace/settings-nav.tsx`（client）；用 `IntersectionObserver` 监听 `general/render/security/billing/integrations/api` 6 个 section 的视口可见度，rootMargin `-30% 0px -55%` 让"中部 30-45%"区段触发激活；初始化读 `window.location.hash` 选中。 |
| P1.13 | `Project.status` 联合包含 `running`（永不出现） | `projects/page.tsx` 改用显式 `PROJECT_IN_PROGRESS: ReadonlyArray<string>` 常量，移除 `running` 分支并加注释说明 Project / Job / RenderTask 三类 status 语义。`Status` 联合本身保留兼容 StatusBadge。 |
| P1.14 | KpiTile sparkline 缺 srHint | 新增 `srHint?: string` prop + 自动从 trend 推导（`describeTrend()`：上升 / 下降 / 平稳）；svg 旁加 `<span className="sr-only">`，盲用户也能感知趋势。 |
| P1.15 | ProjectFilter / ProjectsBoard `role="tablist"` 不完整 | 改 `role="toolbar" aria-label="按用途过滤项目/模板"` + `aria-pressed` 替代 `aria-selected`；TemplateFilter 也用同一范式。删 button 上的 `role="tab"`。 |
| P1.16 | 多处 lucide icon 缺 `aria-hidden` | 用 python 脚本对 12 个文件做安全的正则替换：`<Icon className="h-N w-N" />` → `<Icon className="h-N w-N" aria-hidden />`（仅自闭合且未含 aria 的）；覆盖 settings / brand / projects / team / dashboard / project-detail / topbar / sidebar / mobile-sidebar / create-wizard / video-player / error.tsx。 |
| P1.17 | 7 处 SVG 裸 hex + sidebar / mobile-sidebar 重复 svg | 新建 `components/brand/brand-mark.tsx`（共享 BrandMark 组件，用 useId 生成 gradient id）；新建 `lib/theme.ts`（BRAND + TREND_COLORS 常量），sidebar / mobile-sidebar 接 BrandMark；KpiTile sparkline 改读 TREND_COLORS。 |

### 顺手做的 P2

| # | 报告条目 | 做了什么 |
|---|---|---|
| P2.18 | `meta-tabs.tsx` + `share-link.tsx` setTimeout 未 cleanup | 都加 `timerRef + useEffect cleanup`；不再在卸载后 setState |
| P2.19 | `projects-board.tsx` `status: string` 收窄 | 改 `StatusFilter = "any" \| Status`，select onChange 加显式 cast |
| P2.20 | `meta-tabs.tsx` `<dt>/<dd>` 缺 `<dl>` 包裹 | 用 `<dl>` 包外层 |
| P2.22 | `create-wizard.tsx` 0.0001 与"5%"注释不符 | 改注释为 "0.01%" 并加生产说明 |
| P2.23 | composer "保存草稿" disabled 用 `text.trim()` | 改 |
| P2.28 | `create-wizard.tsx` 重试按钮 `RotateCcw` → `RefreshCw` | 改（与 error.tsx 一致） |
| P2.29 | meta-tabs 评论 "+2 回复" 中文不顺 | 改 "2 条回复" |
| P2.30 | team mobile 卡片视图 presence dot 与 name 重叠 | dot 改 `bottom-0 right-0 translate-x-1/3 translate-y-1/3 rounded-full`，半在 avatar 内；同时改桌面表格行版；meta-tabs 评论 presence dot 同改；都加 sr-only 文本「在线 / 离开 / 离线」 |
| P2.31 | `label.tsx` `peer-disabled` 死代码 | 删 |
| P2.32 | `library` 素材 grid `minmax(180px,1fr)` 360px 溢出 | 改成 `minmax(150px,1fr) sm:minmax(180px,1fr)` |
| P2.34 | `globals.css .skel background-size: 200px` 固定 px | 改 `50% 100%` + `background-repeat: no-repeat`，键帧改 `-50% → 150%` |
| P2 | `<button>` `role="tab"` 已下线 | 同 P1.15 顺手清 |

---

## 跳过 / 留给 ring 004

| 项 | 原因 |
|---|---|
| P2.21 权限矩阵无表格语义 | 当前 div grid + aria 标签足够 SR 用；改 `<table>` 需要重排结构；留 design-language v3 |
| P2.25 `cn()` 替换最后几处模板字符串 | brand 页 / settings 页其它残留；非阻塞 |
| P2.27 ProjectsBoard < sm 没有"更多筛选" sheet | 需新增 sheet 组件 |
| P2.33 sidebar / mobile-sidebar NAV 数组重复 | 抽 `lib/nav.ts` 是小改但跨两文件；留 ring 004 |
| P3 `ProjectsBoard` 用 Card + 自制 header bar 而非 CardHeader | 结构小瑕疵，不影响视觉；留 design-language v3 决定 |
| `app/(app)/` 路由组重构期的新页（analytics / integrations / notifications） | 在并行的 Design ring 中产生，refine 003 只审了已知 8 + 1 页，新页留 test ring 003 审 |

---

## 验收

- `npx tsc --noEmit` → 0 错 ✓
- 12 个路由全 200 ✓（含新的 `/analytics /integrations /notifications`）
- dev server 全程未崩 ✓
- 创建文件 5 个：
  - `components/brand/brand-mark.tsx`
  - `components/workspace/template-filter.tsx`
  - `components/workspace/settings-nav.tsx`
  - `lib/theme.ts`
  - `docs/next-refine-ring-log-003.md`（本文件）
- 编辑文件 17 个（含路由组结构外迁后的 8 页）

---

## 喂回 Design 环 v3 (Design ring 003 input)

### 新设计 token / 抽象（已落地）

1. **`lib/theme.ts` BRAND + TREND_COLORS** — SVG attribute 唯一颜色来源；tailwind config 改色时同步这里。
2. **`<BrandMark />` 共享组件** — sidebar / mobile-sidebar / 未来 marketing / external 页全部走这一个组件。下一轮 Design 应该把 brand 页也接入（替换硬编码 hex 展板的"使用例"）。
3. **`useId()` for SVG gradient id** — pattern：所有内嵌 SVG 需 `<linearGradient id={...}>` 的组件都该用 `useId()` 防 id 冲突。
4. **`preserve-motion` 类** — 任何「关键状态信号」动画（loading spinner、新消息呼吸）必须加 `preserve-motion`，否则 reduced-motion 用户感知不到状态。
5. **`role="toolbar" + aria-pressed`** — 一组互斥按钮（"全部 / 营销 / 培训"）的标准 a11y 写法。Design 应该把这条写进设计语言 v3 的 a11y 章节。
6. **presence dot 位置规范** — `absolute bottom-0 right-0 translate-x-1/3 translate-y-1/3 rounded-full ring-2 ring-card` + sr-only 文本；任何 avatar + 状态点都走这个规范。

### 新设计场景（Design 应该补设计）

- **`/analytics` 页（已结构 placeholder）** — 给 design v3 的真正落地场：让 design 接管 KpiTile + 趋势线 + distribution + timeseries 设计。
- **`/integrations` 与 `/notifications`** — 新加的路由还是空骨架（refine 003 未审），Design 应该用本轮新的 token / 范式（KpiTile sparkline、空态文案、Toolbar filter）填充。
- **`/(external)/share/[token]`** — refine 003 grep 出来在 share 页有 5+ 个独立 video-player 控件（Pause / Volume2 / Maximize2 等），还没接 sr-only 标签。Design 应该把这些 control 收口为 `<VideoControlsBar />` shared 组件（与 internal `/projects/[id]` 共用）。
- **"更多筛选" sheet（移动端）** — ProjectsBoard 在 < sm 隐藏了 status / owner select；要加一个 mobile-only sheet 入口。设计语言 v3 应该定义 sheet 模式（drawer 的兄弟，但是 bottom-up）。
- **权限矩阵桌面 → 移动卡片视图** — team 页权限矩阵 horizontally-scroll 在 360px 不友好，应改成 mobile-only "卡片堆栈"视图（每个 permission 一张卡，包含 5 个 role 的允许状态）。

### Design ring 003 必须沿用的范式

- **8 页头响应式签名**：`flex flex-wrap items-end gap-4 md:gap-6` + h1 `text-[28px] md:text-[34px]`（短标题）/ `text-[26px] md:text-[34px]`（长标题如 create / project-detail）+ CTA 文案 `<span className="hidden sm:inline">` 折叠 → 这是设计语言 v3 的 page-header 默认。
- **filter chip 模式**：`<Button rounded-full + count subspan + aria-pressed>` 是任何「分类 / 标签 / purpose」筛选的默认表达。
- **KpiTile 必带 srHint 或 trend**：盲用户感知数据趋势；没有真实 trend 数据时也要给 `srHint` 文案。
- **autosave + restore banner**：任何 long-form 表单（create / settings / brand 编辑 / new-webhook）的标准范式 — restore banner 顶部 3.5 秒、保存时间戳右上、"清空重来" link。

---

## 隐藏的小事故 · 记录留档

本轮 refine 进行到一半时，发现 working tree 多出来 `app/(app)/...` 路由组 + `app/(external)/...` + 新页 analytics / integrations / notifications — 由 Design ring 在并行工作中产出未 commit 的结构性重构。Refine 顺手适配了新路径（编辑 `app/(app)/X/page.tsx` 而非 `app/X/page.tsx`），但没有自己重命名 — 这些 rename 应由 Design ring 自己 commit。本轮 commit 只包含 refine 触动的内容（修 vibe / a11y / race），rename 留给 Design ring 002 / 003 commit。

---

*Refine ring · pass 003 — 2 P0 + 15 P1 + 11 P2 = 28 项落地，5 新文件 + 17 编辑文件。下一轮（ring 004）应聚焦：新页 analytics / integrations / notifications + (external)/share/* 的 vibe 化、权限矩阵移动端、ProjectsBoard 移动端筛选 sheet、`lib/nav.ts` 抽离。*
