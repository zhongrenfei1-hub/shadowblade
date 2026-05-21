# ShadowBlade Next.js · Test Ring Report 003

审计对象：`frontend-next/` 全部 `.tsx` / `.ts` / `.css`（`node_modules` 除外），重点核查 (1) Design ring 路由组重构 + 4 新页（`58d7e5d`），(2) Refine ring 003 把 test 002 的 2 P0 + 15 P1 + 11 P2 落地（`be51a9d`）
审计日期：2026-05-21
审计员：Test ring · pass 003（只读 · 纯静态分析）
基线：`tsc --noEmit` 0 error ✓
源文件统计：13 路由文件（其中 4 新增）+ 2 layout（新增）+ 26 组件（5 新增：`brand-mark`、`template-filter`、`settings-nav`、`lib/theme.ts`，沿用了 ring 002 的 `mobile-sidebar`、`project-filter`、`projects-board`）

---

## 顶部总表

### 10 类审计维度

| # | 维度 | 评级 | 一句话总结 |
|---|---|---|---|
| 1 | TypeScript 严格性 | **pass** | refine 003 的 white-list 守卫 + StatusFilter 收窄都加上了；新页 `Category` / `Tab` / `Kind` / `Notice` 都是显式 union，无 `as never` |
| 2 | React 模式 | **warn** | refine 003 的 P0.1（createWizard interval race）+ P0.2（mobile-sidebar focus trap）真修了 ✓；但 (external)/share/[token] 引入新的 `setTimeout` 无 cleanup（regression）;analytics KpiTile 不传 trend、回退到 FALLBACK |
| 3 | Tailwind / shadcn | **pass** | shimmer keyframe 双定义清掉 ✓；新页全用 token 调色；integrations 把第三方品牌色入 `style={{ background }}` 是合理（slack/figma/notion 等自有品牌色） |
| 4 | 无障碍 (a11y) | **warn** | KpiTile srHint ✓、role=toolbar+aria-pressed 沿用 ✓、reduced-motion 排除 spinner ✓；但 4 新页有 13 处 lucide icon 缺 aria-hidden、(external)/share 无 `<main>` landmark、integration tabs 缺 `role=toolbar` wrapper |
| 5 | 语义 HTML | **warn** | (external)/share 缺 `<main>`；4 处 `<time>` 缺 `dateTime`；notifications `<aside>` 装 tab 但用 `aria-current="page"` 而非 `aria-pressed` |
| 6 | 中文文案 | **pass** | analytics 「产量在涨，首版耗时在降」、notifications 「全部处理完了」、integrations 「把 ShadowBlade 接到你的工具链里」、share 「不需要 ShadowBlade 账号」全部专业级 |
| 7 | 响应式 | **pass** | 4 新页全部沿用 `flex flex-wrap items-end gap-4 md:gap-6` + `text-[28px] md:text-[34px]` 签名 ✓；analytics 360 / 480 / 768 / 1024 都过；share /[token] 360 也 OK |
| 8 | 性能 | **warn** | 新 share/[token] 与 analytics KpiTile 都是 client 组件全包（不必）；NotificationsPage `setDismissed(new Set(NOTICES.map))` 在 "全部标已读" 时把所有 id 计入 dismissed —— 是 "标已读"，但实际行为是「全部隐藏」 |
| 9 | 品牌一致 | **warn** | BrandMark + lib/theme.ts 落地 ✓ 但只接入了 sidebar / mobile-sidebar；video-player、project-cover、share/[token] 仍各有 19 / 19 / 7 处硬编码 hex；share/[token] 重复了 BrandMark 的 SVG（不用 `<BrandMark />`） |
| 10 | 可用性 / 一致性 | **warn** | sidebar / mobile-sidebar 的 NAV 不含 /analytics / /integrations / /notifications；topbar ROUTE_LABEL 不含 → 面包屑显示英文 slug；settings SECTIONS 列 6 项但 SettingsForm 只渲染 4 个 Card（billing / integrations 死链） |

### 13 个 page 评级（含新增 4 页 + 1 share）

| 路由 | 评级 | 主要问题 |
|---|---|---|
| `/` | **pass** | redirect 不变 |
| `/dashboard` | **pass** | KpiTile 4 个全部喂真 trend ✓；ProjectFilter ✓；refine 003 全部落地 |
| `/create` | **pass** | createWizard 的 interval race / autosave race / draft 白名单全修 ✓；preserve-motion Loader2 ✓ |
| `/projects` | **pass** | PROJECT_IN_PROGRESS 常量 ✓；ProjectsBoard StatusFilter 收窄 ✓ |
| `/projects/[id]` | **warn** | VideoPlayer 仍 7 处硬编码 hex；其余 ✓ |
| `/templates` | **pass** | TemplateFilter 抽出 ✓；空态文案 ✓ |
| `/library` | **warn** | FOLDERS count 接 totals ✓；但 `aria-pressed` 加上了**没有 onClick**——按钮"假可按"，screen reader 读「切换按钮，已选中」点了无反应 |
| `/brand` | **pass** | PALETTE 硬编码 hex 是品牌展板**应有**的，OK |
| `/team` | **pass** | presence dot 重叠修了 ✓；权限矩阵无 table 语义保留（refine 003 主动跳过）|
| `/settings` | **warn** | SettingsNav IntersectionObserver ✓；但 SECTIONS 含 `billing` `integrations` 而 SettingsForm 只渲染 `general / render / security / api` 4 个 Card — 2 个死锚点 |
| `/analytics` ⭐新 | **warn** | KpiTile 不传 trend → 全部 FALLBACK + 自动 srHint 说「近 7 期持续上升」实为假数据；3 个 icon 缺 aria-hidden；柱状图无 caption |
| `/integrations` ⭐新 | **warn** | tab 容器缺 `role="toolbar"`；Plus / ExternalLink 缺 aria-hidden；外链缺 `noreferrer`；empty state 内联不用 EmptyState |
| `/notifications` ⭐新 | **warn** | "全部标已读" = 全部 dismissed（误用语义）；tab 容器 `aria-current="page"` 应为 `aria-pressed`；`<time>` 缺 `dateTime` |
| `/share/[token]` ⭐新 | **warn** | 重新引入 `setTimeout` 无 cleanup（regression）；硬编码 BrandMark SVG（不复用）；9+ icon 缺 aria-hidden；无 `<main>` landmark；2 个 `<time>` 缺 dateTime |

---

## 维度一 · TypeScript 严格性

### pass · ring 002 提的 P2 都修了

- `safeParseDraft` + `pickAllowed` / `pickString` 守卫（`create-wizard.tsx:90-115`）— 白名单完整覆盖 5 个 union。
- `StatusFilter = "any" | Status`（`projects-board.tsx:17`）— select onChange `as StatusFilter` 是合理的运行时 cast。

### pass · 4 新页 union 类型干净

- `analytics`：所有从 api.analytics 拿到的字段都走 `Analytics` 类型；KIND_CLASS 用 `Record<string, string>` 而非 union（小遗憾，应是 `Record<"warn"|"stop"|"ok", string>`）。
- `notifications`：`Kind` + `Tab` 显式 union，`Notice` 严格类型。
- `integrations`：`Category` + `Integration["cat"]` 用 `Exclude<Category, "all" | "connected">` 排除虚拟分类 ✓ 设计干净。

### P2 / `app/(app)/analytics/page.tsx:29` · `KIND_CLASS` 应严格化

```ts
const KIND_CLASS: Record<string, string> = { warn: "...", stop: "...", ok: "..." };
```

`d.kind` 是 `string`（来自字面量 const 数组的 `kind`），实际只可能是 "warn" | "stop" | "ok"。`Record<string, string>` 让 `KIND_CLASS["typo"]` 不报错，丢了拼写检查。

**推荐**：定义 `type DriftKind = "warn" | "stop" | "ok"`，DRIFT 数组的 kind 也用 `as DriftKind`。

### P3 / `app/(app)/notifications/page.tsx:54` · `typeof Check` 取代 `LucideIcon`

```ts
const KIND_ICON: Record<Kind, { icon: typeof Check; cls: string }> = ...
```

`typeof Check` 用单一 icon 的类型推断，比 `import { LucideIcon }` 多一层间接。统一用 `LucideIcon` 类型。

---

## 维度二 · React 模式

### pass · P0.1 createWizard interval race 真修了

```tsx
useEffect(() => {
  if (!running) return;
  const id = setInterval(() => { ... }, 800);
  return () => clearInterval(id);
}, [running]);

function cancel() { setRunning(false); }
```

局部 `const id` 闭包正确捕获；cancel 仅 setState 让 cleanup 接管。**P0 已死透**。

### pass · P0.2 mobile-sidebar focus trap 完整

`mobile-sidebar.tsx:50-101` 完整实现：
- `previouslyFocused` capture + restore on close ✓
- `firstFocusable?.focus()` 初始焦点 ✓
- `getFocusable()` 过滤 disabled + display:none ✓
- Shift+Tab 在 first 时跳到 last，Tab 在 last 时跳到 first ✓
- Esc preventDefault + onClose ✓

**P0 已死透**。

### pass · P1.5 autosave initialMount 跳首次

```tsx
const initialMount = useRef(true);
useEffect(() => {
  if (initialMount.current) { initialMount.current = false; return; }
  const t = setTimeout(() => localStorage.setItem(...), 600);
  return () => clearTimeout(t);
}, [draft]);
```

第一次 setDraft (restore) 不触发 autosave；后续都会。**P1 已死透**。

### P0 / `app/(external)/share/[token]/page.tsx:51` · `setTimeout` 无 cleanup（regression）

```tsx
async function copyLink() {
  ...
  setCopied(true);
  setTimeout(() => setCopied(false), 1800);
}
```

Refine 003 P2.18 刚把 `share-link.tsx` 的同样问题修了（用 `timerRef + useEffect cleanup`），新加的 share/[token] 页又写了一遍**未 cleanup 的 setTimeout**。如果用户复制后立即关 tab 或路由跳走（虽然 external 页路由切换概率低），仍有「setState on unmounted」warning。

**推荐改法**：抄 share-link.tsx 的范式：
```tsx
const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
useEffect(() => () => { if (copyTimerRef.current) clearTimeout(copyTimerRef.current); }, []);
async function copyLink() {
  ...
  setCopied(true);
  if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
  copyTimerRef.current = setTimeout(() => setCopied(false), 1800);
}
```

### P1 / `app/(app)/analytics/page.tsx:82-95` · 4 个 KpiTile 不传 `trend` → FALLBACK 数据 + 误导 srHint

```tsx
{a.kpis.map((kpi, i) => {
  const f = formatKpi(...);
  return <KpiTile ... value={f.value} ... delta={...} positive={...} />;
})}
```

`KpiTile` 看到 `trend === undefined` 走 FALLBACK_TREND `[4, 6, 5, 7, 8, 7, 9]`，自动 srHint 推 `describeTrend(FALLBACK_TREND)` → 永远是「近 7 期持续上升」。但 analytics 的 4 个 KPI 是「本月渲染次数 / 首版耗时 / 通过率 / 节省费用」，第 2 个（首版耗时）正确方向应**下降**，第 4 个（节省）的方向是**上升**。

**结果**：盲用户听到的「持续上升」对耗时是错的语义（耗时上升 = 慢了 = 坏事），实际数据 `delta: -0.31` 说耗时下降了 31%（好）。**前后矛盾的 srHint**。

**推荐改法**：analytics page 应该从 `a.timeseries` 反推每个 KPI 的 7 天 trend，或至少手动写显式 srHint：
```tsx
<KpiTile ... srHint={`${kpi.label} ${f.value}${f.suffix ?? ""}，${formatDelta(kpi.delta)}`} />
```

### P1 / `app/(app)/notifications/page.tsx:82-85` · 「全部标已读」语义错配

```tsx
<Button onClick={() => setDismissed(new Set(NOTICES.map((n) => n.id)))}>
  全部标已读
</Button>
```

`dismissed` 是用来**隐藏**通知的（visible filter 在 67 行排除 dismissed）。"标已读" 应该是把 `n.unread` 翻成 false，**保留通知可见**。当前实现是「全部隐藏」，点完后用户看到 EmptyState「全部处理完了」— 但通知本身没消失（实际是 mock 数据），刷新页面后又全部 unread。

**真实影响**：用户预期「标已读 = 我看过了，但通知仍在」，得到的是「我点了，所有通知都消失了」。这是**功能 bug**。

**推荐改法**：
```tsx
const [readIds, setReadIds] = useState<Set<string>>(new Set());
// ...
onClick={() => setReadIds(new Set(NOTICES.map(n => n.id)))}
// 渲染时
n.unread && !readIds.has(n.id) && <UnreadDot />
```

`unreadCount` 也应该 `NOTICES.filter(n => n.unread && !readIds.has(n.id)).length`。

### P2 / `components/workspace/kpi-tile.tsx:42` · 用 `useId()` 但文件无 `"use client"`

```tsx
import { useId } from "react";
// ...
const reactId = useId();
```

`useId` 在 React 18 server / client 都可用，**理论上不需要 `"use client"`**。但 KpiTile 被引入 `app/(app)/dashboard/page.tsx`（server 异步组件）、`app/(app)/team/page.tsx`（server）、`app/(app)/analytics/page.tsx`（server）——三个 server component 调 KpiTile，Next.js 把 KpiTile 当 server 渲染。`useId` 在 server 跑时**生成的 id 是确定性的、SSR-safe**（基于树位置），不会 mismatch hydration ✓。

但有个细节：KpiTile 没标 `"use client"`，那它的 `<linearGradient id={gradientId}>` 只在 server 渲染一次，client 拿到的就是这个 id。**OK 不出错**。但**`useId` 在 server component 中使用是一个 React 19 才完全稳定的做法**——React 18 文档说 "Components calling useId always go through hydration"，意思是这个组件实际上会被识别为 client component 自动 mark。

**实测验证**：`tsc --noEmit` 0 error；运行时也应 OK。但若未来升 React 19 后 server-only 渲染策略变化，可能需要显式 `"use client"`。**建议加上 `"use client"` 做 future-proof**。

### P2 / `components/brand/brand-mark.tsx:3` · 同 KpiTile，`useId` 在 server component

同样 OK 但建议 `"use client"`。

### P3 / `app/(app)/integrations/page.tsx:63-66` · `counts` 在每次 render 都重算

```tsx
const counts = { all: INTEGRATIONS.length, connected: INTEGRATIONS.filter(i => i.connected).length };
```

INTEGRATIONS 是 module 顶层 const（15 项），每次 render 都跑 filter — 不致命，但应 `useMemo` 或 module-level computed。

---

## 维度三 · Tailwind / shadcn

### pass · P1.3 shimmer keyframe 双定义清掉了

`tailwind.config.ts:71-80` 已删 `keyframes.shimmer`，保留 `animation: "shimmer-slow"`；`pipeline-stage.tsx:30` 用 `animate-shimmer-slow` utility。死代码 `animate-shimmer` 同步消除 ✓。

### pass · P1.6 reduced-motion 排除 spinner

`globals.css:115-127` 的 `*:not(.preserve-motion):not(.preserve-motion *)` 正确排除了 `.preserve-motion` 自身和它的子树。`.animate-fade-up { animation: none; opacity: 1; transform: none; }` 让 reduced-motion 用户直接看到 final state（不入场 6px translate），避免眩晕 ✓。

实测 selector：
- `<Loader2 class="preserve-motion animate-spin">` → 被排除 ✓
- `<Loader2 class="animate-spin">`（无 preserve-motion）→ 仍被吃掉 — refine 003 检查过的 3 处 Loader2 都加了 preserve-motion ✓

### P2 / `app/(app)/integrations/page.tsx:137` · 第三方品牌色入 `style={{ background }}`

```tsx
<span style={{ background: i.color }}>
```

Slack `#4A154B` / Notion `#0f0f0f` / Figma `#F24E1E` / YouTube `#FF0000` 等是**第三方品牌色**，必须保留这些 hex（slack 的紫不能改）。**不算 brand drift**——但应该集中到 INTEGRATIONS 常量里（已经是），并加注释「第三方品牌色，禁止 token 化」。

### P2 / `app/(app)/analytics/page.tsx:111-118` · 柱状图颜色用 utility ✓

```tsx
<div className="rounded-t bg-accent-500/85" />
<div className="rounded-t bg-amber-400/85" />
```

走 token 系统 ✓。`/85` 是 tailwind 标准百分比 alpha。**pass**。

### P2 / `app/(app)/analytics/page.tsx:136-137` · `bg-gradient-to-r from-accent-500 to-sky-400`

分布条用 token gradient ✓。但出现了**两处一样的 gradient**（用途分布 + 画幅占比，137 / 148 行），可考虑抽 `<DistributionBar />` 复用。

### P3 / `app/(external)/share/[token]/page.tsx:198-213` · `disabled={!!decided}` 把所有决定后的按钮 disabled

```tsx
<Button disabled={!!decided} ...>批准 v17</Button>
<Button disabled={!!decided} ...>要求修改</Button>
```

OK 设计意图（决定后不能改），但 disabled 不够 affordant — 应该额外加 `aria-disabled="true"` 或在按钮里加 ✓ 完成态视觉（已选「已批准 / 已要求修改」）。当前的 `className={cn(decided === "approve" && "bg-accent-400")}` 仅在 approve 按钮变深色，reject 按钮还是 outline 状态不直观。

---

## 维度四 · 无障碍 (a11y)

### pass · refine 003 P1.14-16 落地

- KpiTile `srHint` 自动 `describeTrend` ✓（除 analytics 不传 trend 的问题，见维度二 P1）
- ProjectFilter / TemplateFilter / ProjectsBoard `role="toolbar" + aria-pressed` ✓
- 12 文件的 lucide icon 自动加 `aria-hidden` ✓（dashboard / projects / templates / library / brand / team / settings / projects/[id] / create-wizard / topbar / sidebar / mobile-sidebar / video-player / error.tsx 全覆盖）

### P0 / `app/(external)/share/[token]/page.tsx` · 无 `<main>` landmark

外部分享页结构：
```
<div className="min-h-screen bg-background">
  <header>...</header>
  <div className="mx-auto grid...">{所有内容}</div>
  <footer>...</footer>
</div>
```

外部用户用屏幕阅读器进入时，**没有 `<main>` 让用户跳到主内容**——`(app)` layout 有 sidebar + topbar 走 skip-nav，但 external 页不挂 sidebar，本来就没有 skip 链接，**唯一的 a11y 兜底**就是 `<main>`。当前缺失。

**推荐改法**：把第 97 行的 `<div className="mx-auto grid...">` 改为 `<main id="main-content" className="mx-auto grid...">`，并在 header 第一项加 skip-link：
```tsx
<a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:bg-accent-500 focus:text-navy-950 focus:px-2 focus:py-1 focus:rounded">
  跳到主内容
</a>
```

### P1 / `app/(app)/analytics/page.tsx:66-76` · 3 处 lucide icon 缺 `aria-hidden`

```tsx
<Calendar className="h-3.5 w-3.5" />
<Download className="h-3.5 w-3.5" />
<RefreshCw className="h-3.5 w-3.5" />
```

每个都在 `<Button>` 内、按钮已有可见文本「最近 7 天」/「导出 CSV」/「刷新」——icon 应 `aria-hidden`，否则 screen reader 念 "calendar 最近 7 天" / "download 导出 CSV"，重复信息。

### P1 / `app/(app)/notifications/page.tsx:83,87,138` · 3 处 lucide icon 缺 `aria-hidden`

```tsx
<CheckCheck className="h-3.5 w-3.5" />  // 在「全部标已读」按钮内
<SettingsIcon className="h-3.5 w-3.5" /> // 在「通知设置」按钮内
<Icon className="h-3.5 w-3.5" />         // 通知 glyph，外层 span 有 aria-hidden ✓
```

第 138 行的 Icon 外层 span 已 `aria-hidden`，**继承生效**，不必再加。但 83 / 87 仍需补。

### P1 / `app/(app)/integrations/page.tsx:82,181` · Plus + ExternalLink 缺 `aria-hidden`

```tsx
<Plus className="h-3.5 w-3.5" />  // 在 "自建一个" 按钮内
<ExternalLink className="ml-1 inline h-3 w-3" />  // 在外链文本内
```

### P1 / `app/(external)/share/[token]/page.tsx` · 11 处 lucide icon 缺 `aria-hidden`

ShieldCheck(84) / Clock(88) / Check+Copy(91) / Play(158) / Pause+Play(170) / Volume2(178) / Maximize2(181) / Check(200) / X(209) / MessageCircle(239) / Lock(263) — 全部缺 `aria-hidden`。

最严重的是**视频播放器控制栏**：Volume2/Maximize2 在 `<Button aria-label="音量">` / `aria-label="全屏">` 内，screen reader 念「音量 (icon) 全屏 (icon)」加上 icon 的 SVG accessible name = 双读。

### P1 / `app/(app)/integrations/page.tsx:100` · tab 容器缺 `role="toolbar"`

```tsx
<div className="ml-auto flex flex-wrap gap-1.5">
  {TABS.map(t => <button aria-pressed={tab === t.id}>...)}
</div>
```

button 自身 `aria-pressed` ✓ 但外层 `<div>` 缺 `role="toolbar" aria-label="按分类过滤集成"`，破坏 refine 003 推广的范式。其它三处（ProjectFilter / TemplateFilter / ProjectsBoard）都加了。

### P1 / `app/(app)/notifications/page.tsx:94-113` · 分类切换用 `aria-current="page"` 不准确

```tsx
<aside className="grid gap-1" aria-label="通知分类">
  {TABS.map(t => (
    <button onClick={() => setTab(t.id)} aria-current={tab === t.id ? "page" : undefined}>
```

`aria-current="page"` 是给导航链接用的（当前在哪一页）。这里是**应用内 tab 切换**，应该用 `aria-pressed` 或包成 tablist。

**推荐改法**：
```tsx
<aside role="toolbar" aria-label="通知分类" className="grid gap-1">
  <button aria-pressed={tab === t.id}>...
```

或更准确的 tablist 范式（带 panel）：
```tsx
<div role="tablist" aria-label="通知分类" aria-orientation="vertical">
  <button role="tab" aria-selected={tab === t.id} aria-controls="notif-panel" id={`tab-${t.id}`}>
```
配合 `<div role="tabpanel" id="notif-panel" aria-labelledby="tab-active-id">`。

### P2 / `app/(app)/library/page.tsx:64-82` · 文件夹按钮 `aria-pressed` 但无 onClick

```tsx
<button type="button" aria-pressed={active}>
```

`active = i === 0` 永远为 true 给第 0 个。**按钮无 onClick**，点了什么都不发生。但 `aria-pressed` 让 screen reader 念「切换按钮，已选中」——用户以为可以切换。**误导**。

**推荐改法**：要么真做交互（client 组件 + state），要么去掉 `aria-pressed`（这是 P1 refine 003 漏修，因为本来就改了样式但没接交互）。

### P2 / `app/(external)/share/[token]/page.tsx:172,176,251` 与 `notifications/page.tsx:151` · 4 处 `<time>` 缺 `dateTime`

```tsx
<time className="font-mono text-xs text-white">0:16</time>  // share 播放器
<time>{c.when}</time>  // 评论时间「3 分钟前」
<time>{n.when}</time>  // 通知时间「刚刚」
```

`<time>` 元素**必须有 `datetime` 属性**才是合规 HTML — 否则只是显示用，对屏幕阅读器和 SEO 都没意义。播放器的 `0:16` / `0:28` 是视频时间戳，应该 `<time dateTime="PT16S">`。评论的 "3 分钟前" 应该 `<time dateTime={isoTimestamp}>`。

**推荐改法**：notifications NOTICES + share COMMENTS 都加 `whenISO: string`；播放器 `<time dateTime={`PT${seconds}S`}>`。

### P2 / `components/marketing/empty-state.tsx:53-60` · `role="status" aria-live="polite"` 在每次筛选都触发

当用户切换 ProjectFilter 触发空态，screen reader **每次**都念「该分类暂无项目，换一个 tab 试试」——切换频繁会很吵。`role="status"` 适合提示「保存成功」这种偶发事件，不适合常驻空态。

**推荐改法**：去掉 `role="status" aria-live="polite"`，让空态只是普通区块。如果想保留语义化，可以用 `<section aria-label="空状态"`。

### P3 / `app/(app)/team/page.tsx:195` · `Crown` 用 `aria-label="管理员"` 双读

```tsx
{m.role === "工作空间管理员" && <Crown className="h-3 w-3 text-accent-300" aria-label="管理员" />}
```

`<b>{m.name}</b>` 后跟 Crown(aria-label="管理员") 再跟 `<Badge>{m.role}</Badge>`（"工作空间管理员"），SR 念：「Ava Chen 管理员 工作空间管理员」——重复。

**推荐**：Crown 改 `aria-hidden`，Badge 文本足够。

---

## 维度五 · 语义 HTML

### pass · 新页 `<article>` / `<section>` / `<aside>` / `<table>` 使用合理

- notifications 用 `<article>` 包每条通知 ✓
- analytics 用 `<table><thead><tbody>` 排行榜 ✓
- integrations 卡片用 `<article>` ✓
- share/[token] 评论用 `<div>` 不是 `<article>`（小可惜）

### P1 / `(external)/share/[token]/page.tsx` · 缺 `<main>` landmark

详见维度四 P0。

### P2 / `(external)/share/[token]/page.tsx:244` · 评论用 `<div>` 不是 `<article>`

```tsx
{comments.map(c => (
  <div key={c.id} className="grid gap-1.5 rounded-md border ...">
```

每条评论是独立的内容单元，应该是 `<article>`。`(app)/projects/[id]/page.tsx` 的 MetaTabs 评论已经在 `<TabsContent>` 里，用 div 还可接受；share 页评论作为外部审阅核心内容，应该用 article。

### P2 / 4 处 `<time>` 缺 `dateTime` 属性

详见维度四 P2。

### P3 / `app/(app)/analytics/page.tsx:115-122` · 柱状图无 SR 替代

```tsx
<div className="rounded-t bg-accent-500/85" style={{ height: `${approvedH}%` }} aria-label={`${d.day} 通过 ${d.approved}`} />
<div className="rounded-t bg-amber-400/85" style={{ height: `${rejectedH}%` }} aria-label={`${d.day} 驳回 ${d.rejected}`} />
```

每个 `<div>` 都有 aria-label ✓，但 `<div>` 不是 interactive 元素，**screen reader 默认不读 `<div>` 的 aria-label**——除非用户 tab 到（不可能，没 tabindex）或用 reader 的 navigate-by-element。

**推荐改法**：包整个 chart 在 `<figure>` + `<figcaption>`：
```tsx
<figure aria-label="最近 7 天渲染条形图">
  <figcaption className="sr-only">周一 42 条（通过 38、驳回 4）、周二 51 条（通过 47、驳回 4）...</figcaption>
  ...
</figure>
```

---

## 维度六 · 中文文案

### pass · 4 新页 + share 全部高分中文 UX

- analytics: 「产量在涨，首版耗时在降」是品牌一致的「短句、不假大空」语态 ✓
- notifications: 「全部处理完了」「这个分类下没有新的通知」干净 ✓
- integrations: 「把 ShadowBlade 接到你的工具链里。」用动词 + 句号 ✓
- share/[token]: 「不需要 ShadowBlade 账号」/「下一步：审核或直接发布」/「Ava Chen 邀请你审阅这条成片」叙述清晰、礼貌、非命令式 ✓

### P3 / `app/(app)/analytics/page.tsx:24-26` · DRIFT 文案

```ts
{ kind: "warn", title: "色彩偏移 · 2 条成片", desc: "用了 #20D2B5，应为 #22D3B7 · 可一键自动修正" },
```

文案简洁 ✓ 但 `#20D2B5` / `#22D3B7` 都是真 hex，**演示数据合理**。注意 dashboard 同样 hardcode `#20D2B5` / `#22D3B7`（dashboard.tsx:120）——是设计上的呼应，不算 brand drift（这里 hex 是"内容"不是"样式"）。

### P3 / `app/(app)/notifications/page.tsx:36` · 引号嵌套

```ts
body: '「@Ava — 帮看看新片尾？上轮在 TikTok 转化高了约 22%。」',
```

外层单引号 + 内层中文「」+ mdash `—`。**完美**。

### P3 / `app/(external)/share/[token]/page.tsx:35` · 引号

```ts
text: '把 "without lifting a wrist" 换成 "无需抬腕"，中国市场测试更顺。',
```

英文用 ASCII " "，中文用 ""。**合规** — 双语术语对照场景。

---

## 维度七 · 响应式

### pass · 4 新页 + share 头部全部沿用 8 页响应式签名

```tsx
<div className="flex flex-wrap items-end gap-4 md:gap-6">
  <div className="min-w-0 flex-1">
    <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">...</h1>
  </div>
  <div className="flex flex-wrap gap-2 md:gap-3">
    <Button><Icon /> <span className="hidden sm:inline">...</span></Button>
```

analytics ✓ / notifications ✓ / integrations ✓ — 全部对齐 refine 003 推广的范式。

share/[token] 用稍轻量的 `text-2xl md:text-3xl` 因为它是 external 页头（不需要 dashboard 那么大）— OK。

### P2 / `app/(app)/analytics/page.tsx:109` · 柱状图 `h-[240px]` 固定高度

```tsx
<div className="flex h-[240px] items-end gap-3 px-2">
```

240px 在 360 / 480 / 768 / 1024 都看得清，但在窄屏（如 240px PWA 模式）会压缩柱体高度。设计意图明确 ✓ pass。

### P2 / `app/(app)/notifications/page.tsx:94` · `md:grid-cols-[200px_1fr]`

```tsx
<section className="grid grid-cols-1 gap-6 md:grid-cols-[200px_1fr] items-start">
```

< md 时单列，aside 跑到顶 → 通知列表跑到底。aside 有 6 个 tab，垂直堆 6 个 button + count = 高，再下面才是通知。**移动端体验偏差** — aside 可以折叠成 horizontal scrollable chip。可推到 ring 004。

### P2 / `app/(app)/integrations/page.tsx:123` · `lg:grid-cols-3`

```tsx
<CardContent className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 md:p-6 lg:grid-cols-3">
```

15 张卡片，1024px 3 列 = 5 行，每张 article 约 180px 高 — 滚动 900px 看完，OK。720 / 480 / 360 都 OK ✓。

### P2 / `app/(external)/share/[token]/page.tsx:110` · `lg:grid-cols-[1.6fr_1fr]`

```tsx
<section className="grid grid-cols-1 gap-6 lg:grid-cols-[1.6fr_1fr] items-start">
```

< lg 是单列，播放器全宽 ✓ 评论卡跑到下方 — 设计意图 OK。**pass**。

### 6 个页头响应式（360 / 480 / 768 / 1024）

| 路由 | 360px | 480px | 768px | 1024px |
|---|---|---|---|---|
| `/analytics` | ✓ wrap, h1 28px ≈ 360px 边界 ✓ | ✓ | ✓ | ✓ |
| `/notifications` | ✓ h1 「{n} 条未读」短 | ✓ | ✓ | ✓ |
| `/integrations` | ✓ | ✓ | ✓ | ✓ |
| `/share/[token]` | ✓ h1 「春季产品发布 — 智能腕环 · v17」14 字 × 24px ≈ 336px ✓ | ✓ | ✓ | ✓ |
| `(app)/layout` | grid-cols-1 → md:grid-cols-[248px_1fr] ✓ | ✓ | ✓ | ✓ |
| `(external)/layout` | min-h-screen 单容器 ✓ | ✓ | ✓ | ✓ |

**全部通过** — Design ring 在新页严格遵循了 refine 003 的范式。

---

## 维度八 · 性能

### pass · server / client 边界正确

- `(app)/layout.tsx` 是 server component（无 "use client"）✓
- `(app)/analytics/page.tsx` 是 server async ✓ 用 `await api.analytics()`
- `(app)/notifications/page.tsx` 是 client（"use client"，需要 useState 切换 tab）✓
- `(app)/integrations/page.tsx` 是 client（同理）✓
- `(external)/share/[token]/page.tsx` 是 client（需要 useState 播放 / 评论 / decided）✓

### P1 / `(app)/analytics/page.tsx` · KpiTile 不喂真 trend（详见维度二 P1）

性能影响：每个 KpiTile 都跑 `Math.max(...)` / `Math.min(...)` / `sparkline.map` 计算 FALLBACK，本应直接拿真数据。**计算量小，但 srHint 是错的**。

### P2 / `(app)/notifications/page.tsx:67-68` · `dismissed.has(n.id)` 在每次 render 调用 6 次

```tsx
const visible = NOTICES.filter(n => !dismissed.has(n.id)).filter(n => tab === "all" || n.tab === tab);
const unreadCount = NOTICES.filter(n => n.unread && !dismissed.has(n.id)).length;
```

`.has()` 是 O(1) 没问题。但 visible filter 两次 .filter chain 可以合并：
```tsx
const visible = NOTICES.filter(n => !dismissed.has(n.id) && (tab === "all" || n.tab === tab));
```

非性能问题，可读性提升。

### P2 / `(app)/integrations/page.tsx:57-61` · 双重 filter

```tsx
const list = INTEGRATIONS.filter(i => {
  if (tab === "connected") return i.connected;
  if (tab !== "all" && i.cat !== tab) return false;
  return !q || i.name.toLowerCase().includes(q.toLowerCase()) || i.desc.toLowerCase().includes(q.toLowerCase());
});
```

`q.toLowerCase()` 在 filter callback 内调用 N 次（N = INTEGRATIONS.length = 15）— 应提到外面：
```tsx
const qLower = q.toLowerCase();
const list = useMemo(() => INTEGRATIONS.filter(i => { ... qLower ... }), [tab, qLower]);
```

15 项可忽略；扩展到 100+ 项时优化。

### P2 / `lib/api.ts:273-295` · `ANALYTICS_FALLBACK` module-level const

OK — 加载时算一次，永不变。和其它 fallback 模式一致。

### P3 / `(external)/share/[token]/page.tsx:115-143` · 视频海报内嵌 800×450 SVG 在 client render

是 `"use client"` 的 page，整个 SVG 每次 hydration 都会 walk DOM。**OK**——SVG 是静态字符串，浏览器 parse 一次后不重算，性能影响微小。

---

## 维度九 · 品牌一致

### pass · BrandMark + lib/theme.ts 落地

- `components/brand/brand-mark.tsx` ✓ 用 `useId` 防 id 冲突 ✓ 接 `BRAND.accent500` / `BRAND.sky400` ✓
- `lib/theme.ts` ✓ `BRAND` + `TREND_COLORS` 集中
- `sidebar.tsx:59` 与 `mobile-sidebar.tsx:129` 都引入 `<BrandMark />` ✓

### P1 / `(external)/share/[token]/page.tsx:70-80` · 重复了 BrandMark 的 SVG

```tsx
<span className="grid h-7 w-7 place-items-center rounded-md border border-accent-500/30 bg-gradient-to-br from-navy-700 to-navy-900">
  <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none">
    <path d="M4 4L20 12L4 20V14L12 12L4 10V4Z" fill="url(#sm)" />
    <defs>
      <linearGradient id="sm" x1="4" y1="4" x2="20" y2="20">
        <stop offset="0%" stopColor="#22D3B7" />
        <stop offset="100%" stopColor="#38BDF8" />
      </linearGradient>
    </defs>
  </svg>
</span>
```

**几乎一字不差**地把 BrandMark 又写了一遍 — refine 003 P1.17 的目的就是把这种重复消除。**新引入的 share 页又复制了一份**——分散维护点。同时 `id="sm"` 是写死的短 id，与页面内其它 SVG（`bgshare` / `glwshare`）共存，**风险低但破规矩**。

**推荐改法**：
```tsx
import { BrandMark } from "@/components/brand/brand-mark";
// ...
<BrandMark className="h-7 w-7" />  // 复用，size 通过 className 控制
```

**注意**：当前 BrandMark 是 `h-8 w-8` 固定，share 页要 `h-7 w-7` 小一号。需扩展 BrandMark 接受 `size` 或纯 `className`（已支持 className 但里面 `h-8 w-8` 会和外层 className 冲突 — 需 `cn(..., className)` 让外部覆盖）。

### P1 / `(external)/share/[token]/page.tsx:115-143` 视频海报 SVG + `components/workspace/video-player.tsx:17-50` · 同一海报两处实现

share 页的视频海报与内部 video-player 的海报**几乎完全一致**（同样 ACME · 智能腕环 文案、同样 #22D3B7 圆环）— 应该 share/[token] 直接用 `<VideoPlayer />` 组件，而非内联 SVG。**重复 70+ 行代码**。

**推荐改法**：
```tsx
import { VideoPlayer } from "@/components/workspace/video-player";
// ...
<Card className="overflow-hidden">
  <VideoPlayer />
</Card>
```
当前 share 页有自己的 play/pause state + 进度条，VideoPlayer 也有 — 需要先把 VideoPlayer 抽得更通用（接受 `posterSlug` / `onPlayToggle` / `showControls`），共用 80% 逻辑。可推到 ring 004 / design v3。

### P1 / 总计 40 处 SVG 硬编码 hex 残留

- `components/workspace/video-player.tsx` — 7 处（`#15376a` / `#050a18` / `#22D3B7` × 3 / `#F7F9FC` / `#8590A8`）
- `components/workspace/project-cover.tsx` — 26 处（6 个 cover 各 4-5 处）
- `app/(external)/share/[token]/page.tsx` — 7 处（同 video-player 海报）

Refine 003 P1.17 说「lib/theme.ts BRAND 常量」+「BrandMark 共享组件」，但只接入了 sidebar / mobile-sidebar / KpiTile（走 TREND_COLORS）。**video-player、project-cover、share/[token] 海报全部漏掉**。

**推荐改法**：
1. `video-player.tsx` 把内嵌 SVG 改用 `BRAND` 引用：`fill={BRAND.accent500}` / `stopColor={BRAND.navy900}` 等
2. `project-cover.tsx` 同改（注意 6 个 cover 用 6 套深浅蓝渐变 — 抽 `COVER_PALETTES`：`smartwatch / bootcamp / copilot / seriesC / helios / gdpr`，统一从 BRAND 推导）
3. share/[token] 把内联 SVG 改用 `<VideoPlayer />`

### P2 / lib/theme.ts 缺 `navy` / `graphite` 全套

```ts
export const BRAND = {
  accent500, accent400, accent300, navy900, navy800, navy700, navy500,
  paper, graphite300, sky400, amber400, amber300,
} as const;
```

`navy600` / `graphite500` / `accent600` 等都没有。video-player 用 `#15376a`（≈ navy600）和 `#050a18`（≈ 比 navy950 更黑），都不能直接套现有 token。

**推荐**：lib/theme.ts 扩到全 palette（约 30 个 token），或在 BRAND 里加 `navy950: "#060c1a"` 配合 video-player 的 `#050a18`（最接近）。

### P3 / `app/(app)/notifications/page.tsx:60` · billing icon 用 graphite-500 / 200

```ts
billing: { icon: DollarSign, cls: "bg-graphite-500/30 text-graphite-200" },
```

其他 5 个 kind 都用 accent / violet / sky / amber / rose（视觉激励），billing 用 graphite 显著区别（中性 + 不抢眼）— 设计意图 OK ✓。

---

## 维度十 · 可用性 / 一致性

### P0 / sidebar.tsx & mobile-sidebar.tsx · NAV 不包含 3 个新页

```ts
const NAV = [
  { group: "制作", items: [..., /projects, /templates] },
  { group: "素材与品牌", items: [/library, /brand] },
  { group: "工作空间", items: [/team, /settings] },
];
```

**没有 /analytics、/integrations、/notifications**。Design ring 加了 3 新页 + (external)/share，但没更新主导航。用户**只能通过手动输 URL 或外部链接进入这 3 页**。

**推荐改法**：在「工作空间」组加 3 项 + 重新分组（其实 /analytics 应该跟 /dashboard 同组，/integrations 是 /settings 子项，/notifications 应该是 topbar 的 Bell 入口）：

```ts
{ group: "制作", items: [/dashboard, /create, /projects, /templates, /analytics] },
{ group: "素材与品牌", items: [/library, /brand] },
{ group: "工作空间", items: [/team, /settings, /integrations, /notifications] },
```

或者 /notifications 不入 sidebar，topbar 的 Bell icon `aria-label="通知"` 直接 link 到 /notifications（当前 Bell 没接 link，只是 ghost button）：

```tsx
<Button variant="ghost" size="icon" asChild>
  <Link href="/notifications" aria-label="通知"><Bell /></Link>
</Button>
```

### P0 / `components/layout/topbar.tsx:10-19` · ROUTE_LABEL 不含 3 个新页

```ts
const ROUTE_LABEL: Record<string, string> = {
  "/dashboard": "工作台",
  ...
  "/settings": "设置",
};
```

用户进入 /analytics 时，面包屑 fallback 到 `segments[0]` = "analytics" — 屏幕上显示英文 slug 而非「数据分析」。

**推荐改法**：补 3 行：
```ts
"/analytics": "数据分析",
"/integrations": "集成",
"/notifications": "通知",
```

### P1 / `app/(app)/settings/page.tsx:6-13` 与 `components/workspace/settings-form.tsx:41,74,107,142` · SECTIONS 列 6 项，实际只渲染 4 个 Card

```ts
// settings/page.tsx
const SECTIONS = [
  { id: "general", label: "通用" },
  { id: "render", label: "渲染与画质" },
  { id: "security", label: "安全与 SSO" },
  { id: "billing", label: "套餐与计费" },     // ← 没渲染
  { id: "integrations", label: "集成" },     // ← 没渲染
  { id: "api", label: "API 与 Webhook" },
];
```

SettingsForm 的 Card 只用了 4 个 id：`general / render / security / api`。用户在 SettingsNav 上点「套餐与计费」或「集成」，浏览器跳到 `#billing` / `#integrations` 但**页面上没有对应 element**——IntersectionObserver 也观察不到，`activeId` 永远不到这两个值。

**Design ring 003 应补 2 个 Card**：
```tsx
<Card id="billing">...套餐 + 用量</Card>
<Card id="integrations">...集成快速入口，链接到 /integrations 全市场</Card>
```

或者把 SECTIONS 砍到 4 个，与实际渲染一致。

### P1 / `app/(app)/library/page.tsx:67-82` · 文件夹按钮假可按（详见维度四 P2）

`aria-pressed={active}` 在 `active = i === 0` 永远为 false / 仅第 0 个 true，无 onClick — 点了不响应。**Refine 003 改了 className `cn()` 但没把它接成 client 组件**。

**推荐改法**：抽 `<LibraryFolderNav>` client，参考 SettingsNav 范式。或者真 client + 状态 + 筛选 grid。

### P2 / `app/(app)/analytics/page.tsx:64-77` · 三个按钮顶部，但只有 "刷新" 是 primary

```tsx
<Button variant="outline" aria-label="切换时间窗口">最近 7 天</Button>
<Button variant="outline">导出 CSV</Button>
<Button>刷新</Button>
```

"刷新" 是 primary（accent-500 强调色），但语义上「切换时间窗口」/「导出 CSV」更重要。这种数据页 primary 应该是「导出 CSV」（业务出口）— 设计判断题，可商榷。**保留 refine 队列**。

### P2 / `app/(app)/integrations/page.tsx:170-174` · empty state 内联文本

```tsx
{list.length === 0 && (
  <div className="grid place-items-center py-12 text-sm text-muted-foreground">
    没匹配到「{q || tab}」相关的集成。
  </div>
)}
```

不用 `<EmptyState>` 组件 — 与 notifications 不一致（notifications 用了 EmptyState ✓）。

**推荐改法**：
```tsx
<EmptyState icon={Search} title="没有匹配项" description={`换个关键词或分类试试 — 没匹配到"${q || tab}"。`} />
```

### P2 / `app/(app)/integrations/page.tsx:179-182` · 外链 `target="_blank"` 缺 `noreferrer`

```tsx
<a href="https://api.shadowblade.io/v1" target="_blank" rel="noopener">
```

`noopener` 防新窗 access `window.opener`，但 `noreferrer` 防 referrer header 泄漏。最佳实践是两个都加：`rel="noopener noreferrer"`。

### P2 / `app/(app)/notifications/page.tsx:82-89` · 顶部两个 Button 在 < sm 折叠成 icon-only 但「全部标已读」有副作用

```tsx
<Button onClick={() => setDismissed(new Set(NOTICES.map(n => n.id)))}>
  <CheckCheck /> <span className="hidden sm:inline">全部标已读</span>
</Button>
```

在 < sm 设备上只显示 ✓✓ icon — 用户可能误以为是「全部标记」的状态切换，**没有文字提示其会清空全部通知**。即使「标已读」的语义就是把所有通知归零，移动端也应该至少 `aria-label="全部标已读"`。

**推荐改法**：加 `aria-label="全部标已读"`。同时见维度二 P1 ——「全部标已读」语义本身是 bug，应改为「全部隐藏」或「全部清空」更准。

### P3 / `app/(app)/notifications/page.tsx:138` · glyph icon 嵌套在 aria-hidden span 内

```tsx
<span className={cn("mt-0.5 grid h-7 w-7 place-items-center rounded-md", cls)} aria-hidden>
  <Icon className="h-3.5 w-3.5" />
</span>
```

外层 aria-hidden 继承到 Icon ✓ — Icon 本身不需要加 aria-hidden 重复。**pass**，但其它地方的 sweep 应该 consistent。

---

## 特殊检查

### `lib/theme.ts` 完整性

| 检查项 | 状态 |
|---|---|
| accent 500 / 400 / 300 | **pass** |
| navy 全 palette（50-950）| **fail** — 缺 950 / 600 / 200 |
| graphite 全 palette | **fail** — 只有 300 |
| amber 全 palette | **partial** — 400 + 300 |
| sky 全 palette | **partial** — 仅 400 |
| TREND_COLORS | **pass** |

### `BrandMark` 复用情况

| 用到的位置 | 状态 |
|---|---|
| sidebar.tsx | **pass** ✓ |
| mobile-sidebar.tsx | **pass** ✓ |
| share/[token] page header | **fail** — 内联 SVG 重写 |
| /brand page header（理论上的展示位）| N/A — brand 页是 palette 展板，不需要 mark |

### `useId()` SSR 安全

| 检查项 | 状态 |
|---|---|
| KpiTile `useId` 生成 gradientId | **pass** — server / client 一致 |
| BrandMark `useId` 生成 gradId | **pass** |
| project-cover.tsx hardcode `cv1` / `cv2` / ... | **warn** — 多 ProjectCard 复用同一 cover 时 id 冲突 |
| share/[token] hardcode `sm` / `bgshare` / `glwshare` | **warn** — `sm` 短到可能与其它 svg 撞 |

### 4 新页 + share 整体 a11y 评分

| 路由 | aria-hidden 完整 | 语义元素 | landmark | role/aria-pressed |
|---|---|---|---|---|
| `/analytics` | **fail** (3 漏) | ✓ table / section | ✓ (在 (app) layout main 下) | N/A |
| `/notifications` | **warn** (2 漏，但有 aria-hidden 父) | ✓ article / time(缺 dateTime) | ✓ | **fail** (用 aria-current=page) |
| `/integrations` | **fail** (2 漏) | ✓ article | ✓ | **partial** (button 有 aria-pressed，div 无 toolbar role) |
| `/share/[token]` | **fail** (11 漏) | **warn** (div 应是 article) | **fail** (无 main) | N/A |

### `app/(app)/layout.tsx` 与 `app/(external)/layout.tsx` server/client 边界

| 文件 | 是否 client | 是否需要 | 评分 |
|---|---|---|---|
| `app/layout.tsx` | server (无 "use client") | OK，只有 html/body/字体 | ✓ |
| `(app)/layout.tsx` | server | OK，Sidebar / Topbar 自己是 client | ✓ |
| `(external)/layout.tsx` | server | OK，仅 div wrapper | ✓ |

**全部边界正确**。

### `(external)/share/[token]/page.tsx` 视频播放器 z-index 检查

```tsx
<button absolute inset-0 aria-label={playing ? "暂停" : "播放"} />  // line 150
<div absolute inset-x-3 bottom-3>  // line 163
  <button>...</button>  // 174
  <time>...</time>  // 172, 176
  <progress bar>
  <Button>音量</Button>  // 177
  <Button>全屏</Button>  // 180
</div>
```

DOM 顺序：play overlay button → controls div。在 stacking context 相同时，**后渲染的元素在上**——controls div 优先接 click，OK。但 play overlay button 覆盖整个视频区，**click 在 controls 之外的位置触发播放/暂停**——用户点视频海报中部 = 暂停 ✓ 期望。

### 路由组拆分合理性

| 决策 | 评分 | 备注 |
|---|---|---|
| `(app)/` 装登录后的 11 页 | **pass** | sidebar + topbar layout 共享 |
| `(external)/` 装公开访客 | **pass** | layout 无 sidebar，可装登录页 / 状态页 / 分享链接 |
| `(app)/layout.tsx` 不挂 sidebar/topbar 但作为 children consumer | N/A — 它**挂了** sidebar+topbar，refine 003 留档已说明 |

**结构性 ✓** — 路由组重构是干净的。

### `(app)/layout.tsx` 的 `<main>` 与 (external)/share 的对比

```tsx
// (app)/layout.tsx
<main className="grid content-start gap-6 px-4 py-6 md:gap-8 md:px-10 md:py-8">
  {children}
</main>
```

`(app)` 有 `<main>` ✓，所有 (app) 页面继承。

```tsx
// (external)/layout.tsx
<div className="min-h-screen">{children}</div>
```

`(external)` **没有 `<main>`**——share/[token] page 自己也没加 `<main>`，导致 external 页面整体缺 landmark。

**推荐改法**：把 (external)/layout.tsx 改为 `<main className="min-h-screen">{children}</main>`，或要求每个 external page 自加 `<main>`。

---

## Refine 待办队列（按优先级排序）

### P0（必修，阻塞性）

1. **`sidebar.tsx` + `mobile-sidebar.tsx` NAV 不含 /analytics / /integrations / /notifications** — 3 个新页只能手输 URL；NAV 需新增、最好同时抽 `lib/nav.ts` 单一来源（refine 002 P2.33 也提过）
2. **`topbar.tsx` ROUTE_LABEL 不含 3 个新页** — 面包屑显示英文 slug，补 3 行映射
3. **`(external)/share/[token]/page.tsx` 缺 `<main>` landmark** — `(external)/layout.tsx` 改 `<main>` 或 share page 自加；同时加 skip-link
4. **`(external)/share/[token]/page.tsx:51` `setTimeout` 无 cleanup（regression）** — 抄 share-link.tsx 范式

### P1（影响质量）

5. **`(app)/notifications/page.tsx:82` 「全部标已读」语义错配 — dismissed 应改 readIds，保留通知可见**
6. **`(app)/analytics/page.tsx` 4 个 KpiTile 不传 trend → 都走 FALLBACK_TREND，srHint 永远是「上升」误导** — 从 timeseries 推导真 trend，或显式传 srHint
7. **`(external)/share/[token]/page.tsx:70-80` 重复 BrandMark SVG** — 用 `<BrandMark className="h-7 w-7" />`；BrandMark 接受 className override
8. **`(external)/share/[token]/page.tsx:115-143` 视频海报 SVG 复制 VideoPlayer** — 重构为 `<VideoPlayer />` 复用，或抽 `<PosterFrame slug="wearable-hub" />` 共用
9. **video-player.tsx + project-cover.tsx + share page 仍 40 处硬编码 hex** — 接入 BRAND 常量
10. **`(app)/library/page.tsx` 文件夹 `aria-pressed` 但无 onClick — 假可按** — 抽 `<LibraryFolderNav>` client 或去掉 aria-pressed
11. **`(app)/settings/page.tsx` SECTIONS 6 项 vs SettingsForm 4 Card — billing / integrations 死锚** — 补 2 个 Card 或砍 SECTIONS 到 4
12. **`(app)/notifications/page.tsx:94-113` 用 `aria-current="page"` 应为 `aria-pressed` 或 tablist** — 改 toolbar / tablist
13. **`(app)/integrations/page.tsx:100` tab 容器缺 `role="toolbar" aria-label`** — 加上对齐范式
14. **`(external)/share/[token]/page.tsx` 11 处 lucide icon 缺 aria-hidden**
15. **`(app)/analytics/page.tsx` 3 处 + `notifications` 2 处 + `integrations` 2 处 icon 缺 aria-hidden** — 全局 sweep
16. **4 处 `<time>` 缺 `dateTime`** — notifications NOTICES + share/COMMENTS 加 ISO 时间戳；播放器 dateTime=PT16S
17. **`lib/theme.ts` BRAND 缺 navy 600 / 950 / graphite 全套** — 完整 palette 镜像 tailwind config
18. **`(external)/layout.tsx` 加 `<main>` 或在 share page 自加**
19. **`(external)/share/[token]/page.tsx:244` 评论用 `<article>` 而非 `<div>`**

### P2（细节打磨）

20. **`(app)/analytics/page.tsx:29` KIND_CLASS 用 `Record<DriftKind, string>` 严格化**
21. **`(app)/notifications/page.tsx:54` 用 `LucideIcon` 替代 `typeof Check`**
22. **`(app)/notifications/page.tsx:151` 顶部按钮 < sm 折叠 icon-only 时加 aria-label**
23. **`(app)/integrations/page.tsx:179` 外链 rel 改 `noopener noreferrer`**
24. **`(app)/integrations/page.tsx:170` empty state 改用 `<EmptyState>` 组件**
25. **`(app)/analytics/page.tsx:115-122` 柱状图 wrap 在 `<figure>` + `<figcaption>` 给 SR 完整文字替代**
26. **`components/workspace/kpi-tile.tsx + brand-mark.tsx` 加 `"use client"`（future-proof，useId 在 server component 风险）**
27. **`components/marketing/empty-state.tsx` 去掉 `role="status" aria-live="polite"`（每次筛选都通报太吵）**
28. **`(app)/team/page.tsx:195` Crown 改 aria-hidden（Badge 已说明角色，避免双读）**
29. **`(app)/integrations/page.tsx:57` filter 中 `q.toLowerCase()` 提到外层 useMemo**
30. **`(app)/notifications/page.tsx:67` visible filter 合并双 .filter 调用**
31. **`components/workspace/project-cover.tsx` 6 个 cover gradient id (`cv1`..`cv6`) 用 `useId()` 防同 cover 多实例 id 冲突**
32. **`(external)/share/[token]/page.tsx` `id="sm"` 改 `useId()`**
33. **`components/layout/topbar.tsx` 通知 Bell 改 `<Link href="/notifications">`**（当前 ghost button 无 link）

### P3（可不修）

34. **`(app)/analytics/page.tsx:24-26` DRIFT 文案与 dashboard.tsx:120 都用 #20D2B5 / #22D3B7 — 设计呼应保留**
35. **`(app)/notifications/page.tsx` aside 在 < md 折叠成 horizontal scroll chip（移动端 UX 提升）**
36. **`(app)/integrations/page.tsx` 卡片 article 包整组按钮容器（current 实现已 OK）**
37. **`lib/theme.ts` 内 `BRAND` 注释「与 tailwind config 同步」机器化检验（CI 加 script）**

---

## 总体观感

- **Refine ring 003 P0 全部死透**：CreateWizard interval race 修法标准、mobile-sidebar focus trap 实现完整（previouslyFocused + getFocusable filter + Shift+Tab 循环 + Esc preventDefault）—— a11y / 运行时安全两大类 critical bug 都不再阻塞 beta。
- **Refine ring 003 P1 15/15 全部落地**：shimmer 双定义消除、safeParseDraft 白名单守卫、autosave initialMount race、reduced-motion 排除 preserve-motion、TemplateFilter / SettingsNav / BrandMark 三个新组件全部按设计语言 v3 范式抽出 ✓。这一轮的工程质量收敛度**显著**优于 ring 002 → 002 的修复（那一轮 P1 还有几处遗漏）。
- **顺手 11 个 P2 也修了**：share-link / meta-tabs 的 setTimeout cleanup、`<dl>` 语义、composer disabled `text.trim()` 等都顺路清掉，refine 003 的"扫尾"力度比 002 大。
- **最大遗憾**：design ring 加的 4 个新页（包括 (external)/share）质量参差。analytics 不喂 trend 给 KpiTile 是真功能 bug（srHint 误导）、notifications 的「全部标已读」语义错配是 UX bug、share/[token] 重新引入了未 cleanup 的 setTimeout 是 regression、video-player + project-cover + share 全部漏掉 BRAND 接入是品牌一致性 bug。新页质量 **lag 一个 ring**——design ring 没用上 refine 003 输出的范式（BrandMark / TREND_COLORS / role=toolbar）。
- **结构性最差**：sidebar / mobile-sidebar / topbar 都没更新去暴露 3 个新页。Design ring 加路由但没接导航 —— 用户**没有合法路径**进入 /analytics / /integrations / /notifications，只能手输 URL。这是 P0 阻塞，必须在 ring 004 立刻处理。
- **`(external)/layout.tsx` 与 `(app)/layout.tsx` 的拆分非常干净** —— 路由组重构本身是好的设计决定，server/client 边界正确，无 hydration 风险。
- **文案合规度依然 100%**。analytics / notifications / integrations / share 全部高质量中文 UX。
- **TypeScript 0 error，全部 13 路由 200 OK（refine 003 验收数据）**。
- **Refine 003 收敛度评分**：相比 ring 002 → 003，refine 003 把测试报告里的几乎所有可执行项都做了；唯一遗憾是「design ring 并行加的新内容」refine ring 没回头审。这种「先 design 后 refine 但 refine 已经被先前测试报告占满」的协作时序问题，是四环飞轮的天然摩擦点 —— 建议 ring 004 把 refine 队列拆成「上轮残留」+「本轮 design 新增」两列分别走。

修完 P0 共 4 项 + P1 共 15 项后可发 internal beta v0.3。P2 共 14 项推到 ring 004，P3 共 4 项入设计语言 v3 反馈队列。

---

*Test ring · pass 003 — 13 路由（4 新）+ 2 layout（新）+ 5 新组件 + 26 既有组件，扫描完成。下一轮 Refine 应优先处理 #1 #2 #3 #4（导航补全 / 面包屑 / 外部页 landmark / 已修过的 setTimeout regression），紧接 #5（标已读语义错配）+ #6（analytics KpiTile 不喂数据）—— 这些都是用户在 demo 现场会立刻察觉的功能性问题，比品牌一致性的 hex sweep 优先级高。*
