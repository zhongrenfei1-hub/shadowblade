# ShadowBlade Next.js · Test Ring Report 001

审计对象：`frontend-next/` 全部 `.tsx` / `.ts` / `.css`（`node_modules` 除外）
审计日期：2026-05-21
审计员：Test ring · pass 001（只读，不动源）
源文件统计：8 页 + 2 layout + 9 ui + 5 workspace + 2 marketing + 2 lib = 28 个源文件

---

## 顶部总表

### 10 类审计维度

| # | 维度 | 评级 | 一句话总结 |
|---|---|---|---|
| 1 | TypeScript 严格性 | **warn** | 1 处 `as never`、`PERMISSIONS` 元组类型不健康、`api()` 错误回退会吃掉所有非 `try` 错误 |
| 2 | React 模式 | **warn** | 8 页里 3 页是 `'use client'`；fragment-with-key 反模式 1 处、index key 1 处、未用 import 1 处 |
| 3 | Tailwind / shadcn | **pass** | `cn()` 用法稳定、cva 变体定义完整；少量「ui/label.tsx 的 `peer-disabled` 没有匹配 `peer`」之类细节 |
| 4 | 无障碍 (a11y) | **warn** | 播放器叠两个一样 `aria-label="播放"` 的按钮、`<select>` 没有可见 label 在 settings、3 处装饰 SVG 缺 `aria-hidden` |
| 5 | 语义 HTML | **warn** | 8 页全部裸 `<></>` 顶层 fragment（缺 article/page wrapper）；`brand` 的 `<h4>` 跳级（页内只有 h1→h4） |
| 6 | 中文文案 | **pass** | 整体合规，无「赋能/抓手/闭环」；只有 `dashboard:101` 一处感叹号字符 `!`（语义是「提示」icon，可保留） |
| 7 | 响应式 | **fail** | **零** `md:` / `sm:` / `lg:` 断点；248px sidebar + 多个固定 `grid-cols-4` / `grid-cols-[1.4fr_1fr]`，<1024px 直接破布局 |
| 8 | 性能 | **warn** | `create` / `settings` / `projects/[id]` 整页 client；Google Fonts 外链（非 next/font） |
| 9 | 品牌一致 | **warn** | tailwind 已有 `accent-500=#22D3B7`，但 7 个 SVG 用裸 `#22D3B7` / `#F7F9FC` / `#8590A8`、project-cover 全部硬编码 |
| 10 | 可用性 / 一致性 | **warn** | 8 页页头模式高度统一；但「立即开始」CTA 重复（topbar + 多页），返回上一级缺失，404 缺失，loading.tsx 缺失 |

### 8 个 page 评级

| 路由 | 评级 | 主要问题 |
|---|---|---|
| `/` (`app/page.tsx`) | **pass** | 单纯 redirect，无问题 |
| `/dashboard` | **warn** | unused `Play` import；KPI 区无 `aria-labelledby`；裸 `!` 字符当 icon |
| `/create` | **warn** | 整页 client、`<Tabs>` 没有 `<TabsContent>`、原生 `<select>` × 3 没有 chevron |
| `/projects` | **pass** | 干净；只是 `count` 是硬编码与列表不一致 |
| `/projects/[id]` | **fail** | **两个重叠的播放/暂停按钮** 同一个 `aria-label`、整页 client、`<svg>` 当背景缺 `aria-hidden`、所有色值硬编码 |
| `/templates` | **pass** | 仅一处 `t.name.split("·")[0]` 在无 `·` 名字下会回退到全名 |
| `/library` | **pass** | 文件夹按钮无 `aria-pressed`；backend fixtures 有 font 资源前端少 1 项（图标 OK） |
| `/brand` | **warn** | `<h4>` 跳级（h1→h4）；调色板纯展示，硬编码 hex 是预期的 |
| `/team` | **fail** | **Fragment key 缺失**（`<>` 不能带 key）、`as never` 逃逸、index key、邮箱从名字硬编码 |
| `/settings` | **warn** | 整页 client、原生 `<select>` × 3 缺可见 label、`Toggle` 子组件直接定义在文件里（合理但未抽出） |

---

## 维度一 · TypeScript 严格性

### P1 / `app/team/page.tsx:94` · `as never` 是类型逃逸
```tsx
<Badge variant={(ROLE_VARIANT[m.role] || "default") as never}>{m.role}</Badge>
```
`ROLE_VARIANT` 的 value 类型已是字符串，目标是 `BadgeProps["variant"]`。`as never` 是「我放弃了」的信号。

**推荐改法**：把 `ROLE_VARIANT` 显式声明为 `Record<string, BadgeProps["variant"]>`，去掉 `as never`：

```tsx
import type { BadgeProps } from "@/components/ui/badge";

const ROLE_VARIANT: Record<string, BadgeProps["variant"]> = {
  "工作空间管理员": "done",
  "制作人": "rendering",
  "品牌负责人": "review",
  "审核员": "queued",
};
// ...
<Badge variant={ROLE_VARIANT[m.role] ?? "default"}>{m.role}</Badge>
```

### P1 / `app/team/page.tsx:17-24, 121-135` · `PERMISSIONS` 混合元组，类型不健康
`as const` 给的元组解构出 `label: string | boolean`，于是后面要 `label as string` / `cells as boolean[]`。
**推荐改法**：建模成 object 数组（`type Permission = { label: string; admin: boolean; producer: boolean; brand: boolean; reviewer: boolean; viewer: boolean }`）。

### P2 / `lib/api.ts:9-18` · `get()` 的 fallback 吞掉所有错误
任何错误（含 JSON parse、network、5xx）都走 fallback，开发期看不到后端坏掉。
**推荐改法**：fallback 仅在 production 启用 + `console.warn(err)`。

### P2 / `lib/api.ts:141` · `project(id)` 返回联合 `Project | { error: string }` 偷懒
fallback 给的是 `Project`，另一支永远不发生。删 `{ error: string }` 让 404 走 throw。

### P2 / `app/library/page.tsx:17` · `Record<string, React.ReactNode>` 太宽
直接用 `Record<Asset["kind"], React.ReactNode>`。

---

## 维度二 · React 模式

### P0 / `app/team/page.tsx:122-134` · `<></>` 不能带 key
```tsx
{PERMISSIONS.map(([label, ...cells]) => (
  <>
    <div key={String(label)} ...>{label as string}</div>
    {(cells as boolean[]).map((on, i) => (...))}
  </>
))}
```
短 fragment `<>` 不接受 props（包括 key）。`map` 在外面，React 必报「Each child in a list should have a unique key prop」。

**推荐改法**：用具名 fragment 接 key：
```tsx
{PERMISSIONS.map((perm) => (
  <React.Fragment key={perm.label}>
    <div className="...">{perm.label}</div>
    {/* cells ... */}
  </React.Fragment>
))}
```

### P1 / `app/team/page.tsx:126` · `key={i}` 反模式
和上一条同一段：`<div key={i} ...>`。索引 key 在静态表里能跑，但语义不正确。`key={\`${perm.label}-${i}\`}` 即可。

### P1 / `app/dashboard/page.tsx:2` · `Play` 引入但未使用
```ts
import { Video, Clock, CheckCircle2, DollarSign, Play, RefreshCw, Sparkles } from "lucide-react";
```
`Play` 全文件无引用。`next lint` 会 warn。直接删。

### P1 / `app/create/page.tsx:129-136` · `<Tabs>` 没有 `<TabsContent>`
当作「选项卡组」用没有任何 content，是反 Radix 习惯用法。要么补一行 `sr-only` content，要么换成 `Button` + `aria-pressed`。

### P2 / `app/create/page.tsx:60-74` · 模拟流水线的 `setInterval` 没 cleanup
卸载路径上 interval 仍在跑。改用 `useEffect` + return cleanup：
```tsx
useEffect(() => {
  if (!running) return;
  const t = setInterval(() => setStep((s) => s + 1), 800);
  return () => clearInterval(t);
}, [running]);
```

### P2 / `app/projects/[id]/page.tsx:1` · 整页 `'use client'`，但只有播放器交互是 client
分享卡复制按钮、Tabs 都需要 client，但侧栏元数据、SVG 海报、场景列表完全可以 server render。

**推荐改法**：把 client 部分抽成 `<VideoHeader />`、`<ShareLink />`、`<MetaTabs />` 三个小 client component，主 page 改回 server。

---

## 维度三 · Tailwind / shadcn

### pass · `cn()` 调用稳定，cva 变体完整
- `components/ui/button.tsx:7-32` 的 cva 完整覆盖 5 个 variant + 4 个 size + `xl`。
- `components/ui/badge.tsx:5-29` 13 个 variant 直接对齐 `Status` 枚举。

### P2 / `components/ui/label.tsx:14` · `peer-disabled` 没有匹配 `peer`
```tsx
"text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
```
当前使用方式（`<Label htmlFor=...>` 在 input 上方）不会出现 `peer-*`，残留没意义。删掉即可。

### P2 / `app/create/page.tsx:114` · `Badge variant="done"` 当「推荐」用
```tsx
<Badge variant="done" className="text-[9px]">推荐</Badge>
```
`done` 是「已完成」语义。语义上「推荐」更像 `default` 或新增一个 `recommended`。

---

## 维度四 · 无障碍 (a11y)

### P0 / `app/projects/[id]/page.tsx:114-147` · 两个重叠的播放/暂停按钮，同名 `aria-label`
```tsx
<button onClick={() => setPlaying((p) => !p)} className="absolute inset-0 ..." aria-label={playing ? "暂停" : "播放"}>
  {!playing && <span>...</span>}
</button>
// 与下面 bottom-3 的：
<button onClick={() => setPlaying((p) => !p)} className="grid h-9 w-9 ..." aria-label={playing ? "暂停" : "播放"}>
```
屏幕阅读器 tab 两次都听到「播放」，第一个是「点击视频区域」的大热区，第二个是控制条小按钮。

**推荐改法**：给大热区改 `aria-label="切换播放"` 并加 `tabIndex={-1}` 让它退出 tab 序列；控制栏按钮做唯一可达入口。

### P1 / `app/settings/page.tsx:105, 131, 179` · `<select>` 没有可见 label
三个原生 `<select>` 都只有左侧的「**区域** / **默认编码** / **会话时长**」描述文字作为伪 label，但和 `<select>` 没有 `htmlFor`+`id` 绑定。

**推荐改法**：要么用 `<Label>` + `htmlFor`，要么给 `<select>` 加 `aria-label="区域"` 等。

### P1 / `app/projects/[id]/page.tsx:83-112` · 装饰 SVG 缺 `aria-hidden`
大块视频海报 `<svg viewBox="0 0 800 450">` 是装饰，但没有 `aria-hidden="true"`。读屏会读出里面的所有 `<text>`（「ACME · 智能腕环」「你的一天，准时」「无需打断节奏。」）—— 但这些已经在页面其他地方出现，重复读取。

**推荐改法**：`<svg aria-hidden="true">`。

### P1 / `app/library/page.tsx:56-66` · 文件夹按钮缺 `aria-pressed`
左侧文件夹列表是「单选切换」语义。`<button>` 缺 `aria-pressed={f.active}`。

### P2 / `app/dashboard/page.tsx:55` · KPI section 用 `aria-label="关键指标"` ✓ 已有
唯一一处做对的。可以把这个模式推广到其他 section。

### P2 / `components/layout/sidebar.tsx:96` · 当前页指示条仅靠颜色
```tsx
{active && (<span className="absolute -left-3 top-2 bottom-2 w-0.5 rounded-full bg-accent-500" aria-hidden />)}
```
颜色 + 渐变背景。读屏没有「当前页」信号。

**推荐改法**：给 `<Link>` 加 `aria-current={active ? "page" : undefined}`。

### P2 / `app/create/page.tsx:210-217` · 上传按钮的可拖入区缺标签关联
```tsx
<button type="button" className="grid place-items-center gap-3 rounded-lg border-[1.5px] border-dashed ...">
  <Upload className="h-7 w-7 text-accent-300" aria-hidden />
  <b className="font-display text-sm">拖入文件，或点击上传</b>
  ...
</button>
```
没有 `aria-label` 概括。读屏会把整段 children 拼起来，凑合可用。可补 `aria-label="上传素材文件"`。

---

## 维度五 · 语义 HTML

### P1 / 8 个 page 全部 · 顶层 `<></>` fragment
所有 page 都返回 `<>...</>`，意味着外层是 `<main>`（layout 提供），但每个 page 内部缺一个语义包装（`<article>` 或多个独立 `<section>`）。视觉是 sections，但语义层级跳跃。

**推荐改法**：可接受，因为每个 page 内部就是几个并列 `<section>`。但 `/projects/[id]` 应该用 `<article>` 包裹（这是一个独立的「文档」/「内容单元」）。

### P1 / `app/brand/page.tsx:122, 131` · `<h4>` 跳级
页内层级：`<h1>` (page title) → `<CardTitle>` 是 `<h3>` → 直接跳到 `<h4>`。中间没有 `<h2>` / 跨过 `<h3>` 是 fine（CardTitle 算 h3），但 `<h4>` 放在 CardContent 里位置上更像是 `<h5>` / 或者干脆用 `<div role="heading">`。

**推荐改法**：把「该做」/「不要」改成 `<h4>` ✓ 没问题（h3 → h4 合法），但其他页 CardContent 里没有 `<h4>`，是一致性问题。要么这里也用一个加粗 div，要么其他页统一引入 h4。

### P1 / 缺 `loading.tsx` / `error.tsx` / `not-found.tsx`
App Router 推荐的 boundary 文件全无。`api()` fallback 让人感受不到，但 server component 抛错时 UI 会**直接白屏**。

**推荐改法**：在 `app/` 加：
- `app/loading.tsx` —— 显示 skeleton 或 Spinner
- `app/error.tsx` —— 「服务器临时异常」+ retry
- `app/not-found.tsx` —— 404 页

### P2 / `app/team/page.tsx:67-105` · 表格语义 ✓ 正确用 `<table>`
难得见到用 `<table>`，是对的。

### P2 / `components/layout/topbar.tsx:38-47` · 搜索 `<label>` 包 `<input>` ✓
是好习惯，但 `<label>` 不带 `htmlFor`，靠 wrapping 隐式绑定。可接受。

---

## 维度六 · 中文文案

### pass · 整体合规
- 不见「赋能 / 抓手 / 闭环 / 链路」。
- 不用「您」/「请」。
- 短句优先（h1 普遍 14 字以内）。
- 阿拉伯数字 + 中文单位（「4 分钟」「28 秒」「24 席」）。

### P2 / `app/dashboard/page.tsx:101, 104` · 唯一一处 `!` 字符
```tsx
<span className="grid h-6 w-6 place-items-center rounded-md bg-amber-500/15 text-[11px] text-amber-300">!</span>
<div className="text-sm font-semibold">品牌规范偏移</div>
<div className="truncate text-xs text-muted-foreground">2 条成片使用了 #20D2B5——应为 #22D3B7。</div>
```
`!` 是「警示标志」UI 用字符（类似 ⚠️），不是叹号文案。可保留，但更稳的做法是用 lucide `AlertTriangle` icon。

### P2 / `app/projects/[id]/page.tsx:38` · 评论里夹英文原文
```tsx
text: '把 "without lifting a wrist" 换成 "无需抬腕"，中国市场测试更顺。'
```
合理（评论本身是讨论翻译），保留。

### P2 / `app/team/page.tsx:88` · 邮箱由 name 算出来不对
```tsx
<span>{m.name.toLowerCase().replace(" ", ".")}@acme.com</span>
```
拼音名 / 中文名会算出乱七八糟的邮箱（fixtures 全是英文名所以看不出）。fallback 数据里若引入中文成员就崩。

**推荐改法**：在 `Workspace["team"]` 类型上加 `email: string`，从后端来。

---

## 维度七 · 响应式 ★

### P0 · **整个项目零响应式断点**
全文件 `grep "md:|sm:|lg:|xl:"` 只在 `button.tsx` 的 size 变体里出现，没有任何 viewport 级 `md:hidden` / `lg:grid-cols-2`。

具体后果（按宽度）：

| Viewport | 现状 |
|---|---|
| ≥ 1320px | ✓ 设计原稿宽度 |
| 1024–1320px | 主内容区 `grid-cols-[2fr_1fr]` / `grid-cols-4` 还能挤，开始溢出 |
| 768–1024px | sidebar 还在显示但 248px 占了 1/4 宽度，KPI 4 列变窄；project-cover 高度还行 |
| < 768px (`md`) | **sidebar 不退让**，主内容 `grid-cols-3` 项目卡变成单列宽 + 横向溢出；topbar 的搜索框 `max-w-md flex-1` 把面包屑挤掉 |
| < 480px | 完全不可用：sidebar 占了大半屏，create 页的右侧 sticky 卡完全没空间 |

### P0 / `app/layout.tsx:25` · 主网格不让 sidebar 折叠
```tsx
<div className="grid min-h-screen grid-cols-[248px_1fr]">
  <Sidebar />
  ...
</div>
```
没有 `md:grid-cols-[248px_1fr]` 的限定，移动端就这样。

**推荐改法（最小一刀）**：
```tsx
<div className="grid min-h-screen grid-cols-1 md:grid-cols-[248px_1fr]">
  <Sidebar className="hidden md:block" />
  <div className="grid grid-rows-[60px_1fr] min-w-0">
    <Topbar />
    <main className="grid content-start gap-8 px-4 py-6 md:px-10 md:py-8">{children}</main>
  </div>
</div>
```
- sidebar 在 `< md` 完全隐藏（topbar 后续要加抽屉 trigger）。
- main 的 padding 在小屏从 `px-10` 收到 `px-4`。

### P0 / 所有页 · `grid-cols-4` / `grid-cols-3` / `grid-cols-[2fr_1fr]` 等都无断点
逐页修：
- `dashboard:55, 62, 124` — `grid-cols-4 sm:grid-cols-2 md:grid-cols-4` / `lg:grid-cols-[2fr_1fr]` / `md:grid-cols-2 lg:grid-cols-3`
- `create:90, 149, 218` — 同上
- `projects:56` — `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- `projects/[id]:79, 199` — 同上
- `templates:45` — `grid-cols-2 md:grid-cols-3 lg:grid-cols-4`
- `library:45, 92` — `grid-cols-1 lg:grid-cols-[220px_1fr]`
- `brand:45, 75, 120` — `grid-cols-1 lg:grid-cols-[260px_1fr]` / `grid-cols-2 md:grid-cols-4`
- `team:50, 114` — `grid-cols-2 md:grid-cols-4`；权限矩阵在窄屏不可能塞下，需要单独的「卡片视图」
- `settings:72` — `grid-cols-1 lg:grid-cols-[220px_1fr]`

### P0 / `components/layout/sidebar.tsx:115-132` · 底部「Acme 套餐卡」用 `absolute bottom-4`
```tsx
<aside className="sticky top-0 h-screen ... py-5"> {/* py-5 + 大量 nav */}
  <Link>...</Link>            {/* h≈48 + my-2 */}
  <nav className="mt-6 ...">  {/* mt-6 + 3 个 group * (~16 + 4*36) ≈ 480 */}
  </nav>
  <div className="absolute bottom-4 left-3 right-3 ...">  {/* h ≈ 124 */}
</aside>
```
计算：48 + 24 + 480 + 124 ≈ 676px（含 padding）。当 `h-screen` < 700px（笔记本横屏 16:10 = 800×500 也可能）时，**底部套餐卡叠到「设置」导航项上**，并完全没有滚动（aside 没 `overflow-y-auto`）。

**推荐改法**：把 sidebar 改成 flex 列、底部卡用 `mt-auto`，外层加 `overflow-y-auto`：
```tsx
<aside className="sticky top-0 h-screen w-[248px] shrink-0 ... overflow-y-auto flex flex-col">
  <Link>...</Link>
  <nav className="mt-6 flex flex-col gap-1">...</nav>
  <div className="mt-auto rounded-lg ..."> {/* 删掉 absolute / bottom-4 */}
    {/* Acme · 套餐 */}
  </div>
</aside>
```

---

## 维度八 · 性能

### P1 / `app/create/page.tsx:1` & `app/projects/[id]/page.tsx:1` & `app/settings/page.tsx:1` · 整页 client
三个最大的页面都是 `'use client'`。意味着：
- 不能用 server `fetch()`
- 整段树 hydrate 包送到浏览器
- SEO 信号弱

**推荐改法**：把 client 部分抽成命名的小 client component（`<CreateForm />`、`<VideoPlayer />`、`<SettingsToggleRow />`），page 本身改回 server。create 页几乎所有 setState 都是局部的，可以包成一个 `<CreateWizard />`。

### P1 / `app/layout.tsx:16-22` · Google Fonts 走 `<link>`，没走 `next/font`
```tsx
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:..." />
```
- 渲染期发起两个外部请求，阻塞首屏。
- 国内访问 Google Fonts 慢。

**推荐改法**：用 `next/font/google`：
```tsx
import { Inter, JetBrains_Mono } from "next/font/google";
const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });
// <html className={`${inter.variable} ${mono.variable} dark`}>
```

### P2 / `lib/api.ts:11` · 所有 fetch `cache: "no-store"`
合理（dashboard 的「实时」数字），但 `/templates` 这类基本不变的也是 `no-store`。

**推荐改法**：分级：
- `/projects`, `/jobs`, `/render-queue` → `no-store`
- `/templates`, `/workspaces/me` → `next: { revalidate: 60 }`

### P2 / `app/templates/page.tsx:51` · 模板封面是 CSS 渐变 + 静态文本，无图
合理，但加载实际 thumbnail 后要走 `next/image`。

---

## 维度九 · 品牌一致

### P1 / 7 个 SVG 文件 · 硬编码强调色 `#22D3B7`
- `app/projects/[id]/page.tsx:101, 103`
- `components/workspace/project-cover.tsx:13, 50, 52, 67`
- `components/layout/sidebar.tsx:63` （logo gradient stop）

tailwind config 的 `accent-500 = #22D3B7` 已经定义。SVG 内嵌 hex 是允许的（SVG attribute 不能用 Tailwind class），但**会脱离设计 token**。

**推荐改法 A（保守）**：保留 hex，但把 hex 提到 lib：
```ts
// lib/theme.ts
export const BRAND = { accent: "#22D3B7", navy900: "#0a1428", graphite300: "#8590A8", paper: "#F7F9FC" } as const;
```
SVG 里 `fill={BRAND.accent}`。

**推荐改法 B（彻底）**：让 SVG 用 `currentColor`，外层 wrapper 加 `text-accent-500` class——这是 `hero-illustration.tsx` 已经在用的模式，可以拷贝。

### P2 / `app/dashboard/page.tsx:104` · 文本里写错的 hex `#20D2B5`
这是设计上故意写错的（演示「品牌偏移」UI），保留。

### P2 / `app/brand/page.tsx:13-21` · 调色板硬编码 ✓ 预期
这是设计 token 展板，需要直接给用户看 hex。pass。

---

## 维度十 · 可用性 / 一致性

### P1 / 缺 404 / loading / error
见维度五。

### P1 / `topbar.tsx:56-61` + 7 个 page 的 header · 「一键生成视频」/「新建视频」CTA 三处重复
- topbar 右上角永远显示「一键生成视频」（→ /create）
- `dashboard:46-50` 显示「一键生成视频」按钮
- `projects:30-34` 显示「新建视频」按钮
- `templates:29-33` 显示「自定义新建」按钮

CTA 重复用户体验上**冗余**（topbar 已经常驻），但对营销页可接受。最大问题是文案不一致：「一键生成视频」/「新建视频」/「自定义新建」三种说法。

**推荐改法**：术语表里只写「新建视频」。topbar 改成「+ 新建视频」（只显 icon + 短词），dashboard / projects / templates 都跟一致。

### P1 / `projects:9-14` · `count` 是 hardcode，与 `items.length` 不一致
```tsx
const FILTERS = [{ id: "all", label: "全部", count: 38 }, ...];
// 同时 items 只有 6 个（PROJECT_FALLBACK）
```
"全部 38" 但下面只 6 张卡。视觉割裂。

**推荐改法**：把 count 从 `api.projects()` 的 `total` 拿，按 purpose 在客户端 group。

### P1 / `library/page.tsx:9-15` · 文件夹 count 是 hardcode
同上：「全部素材 112」但 `items` 只 8 项。

### P2 / `dashboard:119-122` · 类别 tab 是 hardcode 不可点
```tsx
{["全部", "营销", "培训", "演示", "社交"].map((t, i) => (
  <Button key={t} size="sm" variant={i === 0 ? "default" : "outline"}>{t}</Button>
))}
```
没有 onClick。点了什么都不发生。

### P2 / `projects:40-50` & `library:53-67` & `settings:74-84` · 三种「左侧导航/筛选」的设计不一致
- `projects` 用 rounded-pill `<Button>`
- `library` 用左对齐 `<button>`，hover `bg-white/[0.04]`
- `settings` 用 `<a href="#anchor">` 块状

应该收成两种：「平铺 chip」（pills）vs「列表 nav」（block）。当前混在一起。

### P2 / `topbar:22` · 面包屑算法用 `decodeURIComponent(segments[1])`
ok。但当 segments[1] 是数字（e.g. `/projects/101`）时显示「101」，没有上下文。

**推荐改法**：对于 `/projects/[id]`，第二段应该显「春季产品发布 — 智能腕环 #101」，需要在 page 内用 React Context 或者 Server Component 改面包屑数据。短期内显「项目 #{id}」更清晰：
```tsx
{segments[0] === "projects" && segments[1] && (<>...<b>项目 #{segments[1]}</b></>)}
```

---

## 特殊检查

### `app/create/page.tsx` · 一键生成体验
| 点 | 状态 |
|---|---|
| 大按钮显眼 | **pass** — `size="xl"` + accent 阴影 + sticky |
| 进度条 | **warn** — 进度只是 setTimeout 模拟，无错误状态 |
| 错误状态 | **fail** — 没有「失败重试」分支；网络断了 UI 没反应 |
| 加载状态 | **pass** — `Loader2 animate-spin` + 步数显示 |
| 表单可恢复 | **fail** — 刷新页面所有 state 丢失（应该 `localStorage` 草稿） |
| 取消按钮 | **fail** — 跑流水线时没法 cancel |

**最小补丁**（在 `start()` 之后增加一个失败/取消分支）：
```tsx
const [error, setError] = useState<string | null>(null);
// ... 在 setInterval 之外加：
function cancel() { setRunning(false); setStep(0); }
// JSX 加：
{running && <Button variant="outline" onClick={cancel}>取消</Button>}
{error && <div role="alert" className="rounded-md bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}
```

### `app/projects/[id]/page.tsx` · 视频播放器
| 控件 | 状态 |
|---|---|
| Play / Pause | **warn** — 两个按钮叠在一起，重复 aria-label（见 a11y P0） |
| 全屏 | **fail** — 仅有 icon，没有 `onClick={() => document.fullscreenElement ? ...}` |
| 音量 | **fail** — 仅有 icon，没有 onClick / slider |
| 进度条 | **fail** — 是静态 `w-[60%]` 装饰条，不可拖拽 |
| 时间显示 | **fail** — `0:16.8` / `0:28.0` 都是字面量 |
| 键盘可达 | **fail** — 没有 Space/← →/M/F 快捷键 |

播放器目前是**纯视觉 mock**。若是「未来接 video」是可接受的占位，但应该在代码里加注释；当前完全没有注释会让人误以为是 work-in-progress 实现。

### `lib/api.ts` ↔ `backend/app/services/fixtures.py` 对账
| 端点 | fixture 是否一致 |
|---|---|
| `projects` | ✓ 6 项，id/name/status/cover 全对齐 |
| `jobs` | ✓ 6 项，stage / progress / runtime 对齐 |
| `assets` | **mismatch** — backend 有 10 项（含两个 font 资源），frontend `ASSET_FALLBACK` 只有 8 项；frontend `totals.font: 4 / logo: 3` 对，但 items 里 logo 给的 `kind: "logo"`，backend 给的 `kind: "image"`（slug 含 "logo"）。**fixtures 类型不一致**。 |
| `templates` | **mismatch** — backend 有 8 项，frontend 6 项（少 `recap-monthly` / `press-quote`） |
| `render_queue` | **mismatch** — backend 5 项，frontend 3 项 |
| `workspace` | ✓ 一致 |
| `analytics` | ✓ 一致 |
| `brand_kit` | ✗ **frontend 完全没用这个 endpoint** —— `app/brand/page.tsx` 里 `KITS` / `PALETTE` 全 hardcode |

**修复要点**：
1. `lib/api.ts:177-186` 补 font 资源、修 logo 的 `kind` 为 `"image"`（或反过来约定 logo 是独立 kind）。
2. `lib/api.ts:188-195` 补 `recap-monthly` / `press-quote` 两个模板。
3. `lib/api.ts:197-201` 补两个队列项。
4. `app/brand/page.tsx` 调用 `api.brandKits?.()` 取数据，删掉 `KITS` hardcode。

### sidebar 重叠风险
**确认存在** — 见维度七 P0 / sidebar 部分。

---

## Refine 待办队列（按优先级排序）

### P0（必修，无法上线）
1. **`app/team/page.tsx:122` Fragment 不能带 key** — 改 `React.Fragment` 具名 + 把 PERMISSIONS 改 object 数组（同时解决 P1.2 / P1.3）
2. **`app/projects/[id]/page.tsx:114-147` 两个播放按钮同 aria-label** — 大热区改 `aria-label="切换播放" tabIndex={-1}`
3. **整站零响应式断点** —— 至少在 `app/layout.tsx:25` 给 grid 加 `md:` 前缀 + sidebar `hidden md:block`
4. **`components/layout/sidebar.tsx:115` 底部 absolute 卡片在矮屏会盖 nav** —— 改成 `mt-auto` + 外层 `overflow-y-auto flex flex-col`

### P1（影响质量）
5. **`app/team/page.tsx:94` `as never` 逃逸** —— `ROLE_VARIANT` 加显式 `Record<string, BadgeProps["variant"]>`
6. **`lib/api.ts:9` fallback 吞错误** —— `process.env.NODE_ENV` 守卫 + `console.warn`
7. **缺 `loading.tsx` / `error.tsx` / `not-found.tsx`** —— 各加一个 server component boundary
8. **`app/dashboard/page.tsx:2` unused `Play` import** —— 删
9. **`app/create/page.tsx:60-74` `setInterval` 没 cleanup** —— 改 `useEffect`
10. **`app/create/page.tsx:129` `<Tabs>` 无 `<TabsContent>`** —— 补 `sr-only` content 或换 button 组
11. **`app/settings/page.tsx:105,131,179` `<select>` 无 label** —— 加 `<Label htmlFor>` + id
12. **整页 `'use client'`** —— `create` / `projects/[id]` / `settings` 抽 client 子组件，page 退回 server
13. **Google Fonts `<link>` → `next/font/google`** —— `app/layout.tsx:16-22`
14. **fixtures 不对账** —— `lib/api.ts` 的 `ASSET_FALLBACK` / `TEMPLATE_FALLBACK` / `QUEUE_FALLBACK` 补齐到 backend
15. **`app/brand/page.tsx` 不调 `api.brandKits()`** —— 接 `lib/api.ts` 新 endpoint + 删 `KITS` hardcode

### P2（细节打磨）
16. **`projects:9` / `library:9` count hardcode** —— 接真实 `total`
17. **CTA 文案三态** —— 统一为「新建视频」
18. **`dashboard:119` 类别 tab 没 onClick** —— 加 state 过滤
19. **7 个 SVG 硬编码 `#22D3B7`** —— 抽 `lib/theme.ts` 常量
20. **`lib/api.ts:141` `project()` 返回联合类型偷懒** —— 删 `{ error: string }` 分支
21. **`components/ui/label.tsx:14` `peer-disabled` 死代码** —— 删
22. **`app/projects/[id]/page.tsx:83` 装饰 SVG 缺 `aria-hidden`** —— 补
23. **`components/layout/sidebar.tsx:96` 当前页指示靠颜色** —— 加 `aria-current="page"`
24. **`app/library/page.tsx:56` 文件夹按钮缺 `aria-pressed`** —— 补
25. **`topbar:22` 面包屑显示数字 id 无上下文** —— 加「项目 #」前缀
26. **`app/team/page.tsx:88` email 从 name 推导** —— 类型加 `email` 字段
27. **「marketing/empty-state.tsx」「marketing/hero-illustration.tsx」无人使用** —— 要么用起来（dashboard 空态），要么删

---

## 总体观感

- **设计与品牌语言极其稳定**：tailwind token 完整、配色克制、字体栈合理、shadcn 变体齐全。是审过的 ring 里**视觉 polish 最高**的一个。
- **真正的工程债务在「响应式 / 边界文件 / 性能默认值」三块**：项目几乎只考虑了 ≥1320px 桌面，移动端不存在；缺 loading/error/404；3 个核心页整页 client 让 hydration 包很大。
- **一个真实 React bug**（team 页 Fragment key）+ **一个真实 a11y bug**（播放器双按钮）是必须修的。
- **fixtures 与后端漂移**让前后端切换会有「素材数不一致 / 模板少两个」的不一致体验。
- **文案合规度高**，几乎不用动。

修完 P0+P1 共 15 项后可发 internal beta；P2 在 ring 002 处理。

---

*Test ring · pass 001 — 28 文件、3,234 行（含 lib/api.ts 的 fixtures），扫描完成。*
