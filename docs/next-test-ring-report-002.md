# ShadowBlade Next.js · Test Ring Report 002

审计对象：Design v2 新增 / 改动的 4 页 + 3 个 layout（route group 重组）
审计日期：2026-05-21
审计员：Test ring · pass 002（只读，不动源 · 纯静态分析）
基线：`tsc --noEmit` 0 error · Next 14.2.18
源文件（共 7 个 · 922 行）：
- `app/layout.tsx`（36 行 · root 瘦身，仅 html/body/字体/metadata）
- `app/(app)/layout.tsx`（18 行 · sidebar + topbar + `<main>`）
- `app/(external)/layout.tsx`（5 行 · 裸壳）
- `app/(app)/analytics/page.tsx`（217 行 · server）
- `app/(app)/notifications/page.tsx`（161 行 · client）
- `app/(app)/integrations/page.tsx`（186 行 · client）
- `app/(external)/share/[token]/page.tsx`（299 行 · client）

v1 已审 8 页本轮不重审。

---

## 顶部总表

### 10 类审计维度（本轮范围内）

| # | 维度 | 评级 | 一句话 |
|---|---|---|---|
| 1 | TypeScript 严格性 | **warn** | 3 处类型偷懒：`KIND_CLASS: Record<string,string>` / `counts[t.id as ...]` / `typeof Check`；`formatKpi(label)` 收参不用 |
| 2 | React 模式 | **warn** | share/[token] 整页 client（299 行）可拆 server；notifications 「全部标已读」实际是 dismiss，TABS 计数固定不更新 |
| 3 | Tailwind / shadcn | **warn** | integrations `Input` import 未用；`transition-colors` + `transition-all` 同时挂；share 没复用 `<VideoPlayer />` |
| 4 | 无障碍 (a11y) | **fail** | analytics `<div aria-label>` 多数 SR 忽略；share 双按钮 aria-label 同名（v1 已修 bug 回归）；`<time>` 缺 dateTime |
| 5 | 语义 HTML | **warn** | h1 单次 ✓ / `<header>` `<footer>` ✓；但 `<b>` 当卡片标题、通知 `.text-sm.font-semibold` 应当 `<h3>` |
| 6 | 中文文案 | **pass** | 整体合规；仅 integrations 空态 `没匹配到「connected」` 英文 id 泄漏；share `token {params.token}` 全串渲染 |
| 7 | 响应式 | **warn** | hero / KPI / 双栏 → 单栏都对；share 顶 sticky header < 480 拥挤；analytics 顶按钮组缺 mobile aria-label |
| 8 | 性能 | **warn** | share 整页 client；notifications / integrations hero 可 server；analytics ✓ |
| 9 | 品牌一致 | **fail** | share/[token] 内联 SVG 7+ 处裸 hex（`#22D3B7` `#15376a` `#F7F9FC` `#8590A8`），v1 已收敛违规又被复制 |
| 10 | 跨页面一致 | **warn** | hero 模式 ✓；但 share 走自己一套 header/footer 不复用；loading / not-found / error 未跟随 route group 拆 |

### 4 个新 page 评级

| 路由 | 评级 | 主要问题 |
|---|---|---|
| `(app)/analytics` | **warn** | 柱图 a11y · `maxRendered` 不抗 0 · `<b>` 当姓名 · `KIND_CLASS` 类型偷懒 |
| `(app)/notifications` | **warn** | "标已读" 实为 dismiss · TABS 计数固定 · `<time>` 缺 dateTime · 整页 client |
| `(app)/integrations` | **fail** | **search + tab 不正交**（connected tab 下 q 被忽略）· `Input` import 未用 · 空态英文 id |
| `(external)/share/[token]` | **fail** | **双 aria-label 重复 v1 已修 bug** · 整页 client 299 行 · 内联 SVG 大量硬编码 · brand logo 跳 `/` 漏入 (app) |

### Route group 重组评级

| 维度 | 评级 | 一句话 |
|---|---|---|
| route group 重组 | **pass** | (app)/(external) 分组干净；root 瘦身合理；唯一遗留是 `app/loading.tsx` / `not-found.tsx` 还在 root，外部访客也会用到 |

---

## 维度一 · TypeScript 严格性

### P1 / `app/(app)/analytics/page.tsx:29` · `KIND_CLASS: Record<string, string>` 太宽
```ts
const KIND_CLASS: Record<string, string> = { warn:..., stop:..., ok:... };
```
`DRIFT.kind` 是字面联合 `"warn" | "stop" | "ok"` 但 KIND_CLASS 用 `Record<string, string>`，typo 不报。
**改法**：`type DriftKind = "warn" | "stop" | "ok"; const KIND_CLASS: Record<DriftKind, string>`，并把 `DRIFT` 标 `{ kind: DriftKind; ... }[]`。

### P2 / `app/(app)/analytics/page.tsx:35` · `formatKpi(label, …)` 接 `label` 不用
函数体里 `label` 从未出现。删它，或注释「保留给将来按 label 走特殊格式」。

### P2 / `app/(app)/integrations/page.tsx:116` · `counts[t.id as "all" | "connected"]` 逃逸
外层有 `(t.id === "all" || t.id === "connected")` 守卫，但 TS narrow 不过 `||`。**改法**：抽 `const isMeta = ...`，把 `counts` 类型化为 `Record<"all" | "connected", number>` 后 narrow。

### P2 / `app/(app)/notifications/page.tsx:54` · `KIND_ICON` 用 `typeof Check` 当 icon 类型
```ts
const KIND_ICON: Record<Kind, { icon: typeof Check; cls: string }> = ...
```
**改法**：`import type { LucideIcon } from "lucide-react"`，跟 EmptyState / KpiTile 风格统一。

### P2 / `app/(app)/notifications/page.tsx:31` · `Notice.actions` 元素无 id
`key={a.label}` 在同名按钮（如两个「查看」）下会重复。加 `id` 字段或 `key={`${n.id}-${i}`}`。

### P3 / `app/(external)/share/[token]/page.tsx:39` · `params: { token: string }` Next 14 OK，Next 15 需 `Promise`
当前同步可用 ✓。升 Next 15 时会 break，留 TODO。

---

## 维度二 · React 模式

### P0 / `app/(external)/share/[token]/page.tsx:1` · 整页 `'use client'` 299 行
share 页除 playing / decided / copied / draft 4 个 state 外，header / footer / 海报 SVG / 链接信息表 全是静态。整页 client 让外部访客（带宽敏感场景）拉一份 299 行 JS + 11 个 lucide icon + textarea/avatar/badge。

**改法**：page 改 server，把 4 个交互各抽小 client：
- `<SharePlayer />`、`<DecisionPanel />`、`<CopyLinkButton />`、`<CommentThread initial={COMMENTS} />`

跟 v1 把 `projects/[id]` 拆 `<VideoPlayer/>` + `<MetaTabs/>` + `<ShareLink/>` 是同一套路。

### P1 / `app/(app)/notifications/page.tsx:65,82` · `dismissed` 与「未读」语义混淆
```ts
const [dismissed, setDismissed] = useState<Set<string>>(new Set());
...
onClick={() => setDismissed(new Set(NOTICES.map((n) => n.id)))}>
  全部标已读
```
按钮叫「标已读」，但点击后 `dismissed.has(n.id)` 把所有 notice 从 visible 过滤掉 — 列表变空，触发 EmptyState。语义错位：「标已读」应清除 unread 标记，「全部归档」才是当前实现。

**改法**：分 `read: Set<string>` / `dismissed: Set<string>` 两 state，按钮先改 `setRead(...)`。

### P1 / `app/(app)/notifications/page.tsx:45-52` · `TABS` 计数模块级 hardcode 不更新
```ts
const TABS = [
  { id: "all", label: "全部", count: NOTICES.length },
  { id: "approvals", label: "审批", count: NOTICES.filter(...).length },
  ...
];
```
dismiss 后侧栏 "全部 8" 仍显示 8，但右侧列表为空。**改法**：包 `useMemo(() => getTabs(NOTICES, dismissed), [dismissed])` 在组件内。

### P2 / `app/(external)/share/[token]/page.tsx:46-53` · `copyLink` `catch {}` 静默失败
非 secure context（http://非 localhost、file://）下 `clipboard.writeText` 抛错，用户点完毫无反馈。
**改法**：`catch (e) { setError("浏览器拒绝了复制操作"); }`。

### P2 / `app/(external)/share/[token]/page.tsx:51` · `setTimeout` 无 cleanup
若组件在 1.8s 内卸载，会在 unmount 后 setState。挂 ref + clearTimeout。

---

## 维度三 · Tailwind / shadcn

### P1 / `app/(app)/integrations/page.tsx:7` · `Input` import 未用
line 7 `import { Input } from "@/components/ui/input";` 实际 line 92-98 用裸 `<input>` 嵌在 `<label>` 内。**改法**：删 import，或改用 `<Input>` 配合 search icon 绝对定位。

### P1 / `app/(app)/integrations/page.tsx:128-129` · `transition-colors` 与 `transition-all` 冲突
```tsx
className={cn(
  "... transition-colors",            // ← 第 128
  "hover:-translate-y-0.5 ... transition-all",  // ← 第 129
  ...
)}
```
`twMerge` 保留最后的 `transition-all` 丢掉 `transition-colors`，net 效果是 `transition: all`（含 transform / shadow），其实正是作者想要的，但 intent 混乱。**改法**：删第 128 的 `transition-colors`，把 `transition-all` 提到 base。

### P1 / `app/(external)/share/[token]/page.tsx:113-184` · 未复用 `<VideoPlayer />`
`components/workspace/video-player.tsx` 已在 v1 refine ring 抽出并修过：
- SVG `aria-hidden="true"`
- 大热区 `tabIndex={-1}` + `aria-label="切换为暂停 / 切换为播放"`
- 底部小按钮 `aria-label="暂停 / 播放"`

share 粘了一整份重写。**改法**：扩 `<VideoPlayer />` 加 `watermark?: string` 后 share 改 `<VideoPlayer watermark="DRAFT · v17" />`，省 ~70 行 + 一次解决 a11y P0（维度四）+ 品牌 hex P0（维度九）。

### P2 / `app/(app)/notifications/page.tsx:134` · `bg-accent-500/[0.022]` 极小任意值
非标准 alpha。改 `/[0.02]` 或上 token。

### P2 / `app/(app)/analytics/page.tsx:32` · `bg-accent-500/[0.05]` 任意值
Tailwind 已有 `/5` 简写。统一。

---

## 维度四 · 无障碍 (a11y)

### P0 / `app/(app)/analytics/page.tsx:116-117` · 柱状图 `<div aria-label>` 不被 SR 读
```tsx
<div className="rounded-t bg-accent-500/85" style={{ height: `${approvedH}%` }}
     aria-label={`${d.day} 通过 ${d.approved}`} />
<div className="rounded-t bg-amber-400/85" style={{ height: `${rejectedH}%` }}
     aria-label={`${d.day} 驳回 ${d.rejected}`} />
```
`<div>` 默认无 role，VoiceOver / NVDA 多数会忽略 `aria-label`。
**改法 A（最小）**：加 `role="img"`。
**改法 B（更标准）**：包 `<figure>` + 同步一份 `sr-only` `<table>` 把 7 天数据列给 SR。

### P0 / `app/(external)/share/[token]/page.tsx:150-161 + 163-171` · 双按钮 aria-label 同名 — v1 已修 bug 回归
```tsx
<button ... aria-label={playing ? "暂停" : "播放"}>  ← 大热区，覆盖整个 video
<button ... aria-label={playing ? "暂停" : "播放"}>  ← 底部小按钮
```
SR tab 时读「播放、播放」两次。这是 v1 test ring 001 在 `projects/[id]` 标 P0 的同一 bug，refine 已经修，share 又自己写一遍。
**改法**：复用 `<VideoPlayer />`（维度三 P1）。

### P1 / `app/(app)/notifications/page.tsx:151` · `<time>` 缺 `dateTime`
```tsx
<time className="...">{n.when}</time>  // n.when = "刚刚" / "3 分钟前"
```
非机器可解析的内容必须配 `dateTime`。**改法**：数据加 `whenISO`，`<time dateTime={n.whenISO}>{n.when}</time>`。

### P1 / `app/(external)/share/[token]/page.tsx:172,176,251` · `<time>` 同问题
- line 172/176：`0:16` `0:28` 是时长不是 datetime，改 `<span>`
- line 251：评论时间 `{c.when}` 同 notifications

### P1 / `app/(app)/analytics/page.tsx:163` · `<table>` 缺 `<caption>`
加 `<caption className="sr-only">最近 30 天制作人排行</caption>`。

### P2 / `app/(app)/integrations/page.tsx:154-158` · 装饰圆点缺 `aria-hidden`
旁边已有「已连接 / 未连接」文字，圆点是纯装饰，加 `aria-hidden`。

---

## 维度五 · 语义 HTML

### pass · share/[token] 用了 `<header>` (line 67) `<footer>` (line 287) ✓

### P2 / `app/(app)/notifications/page.tsx:141` · 通知标题应 `<h3>`
```tsx
<article ...>
  <div className="text-sm font-semibold">{n.title}</div>   ← 应当 <h3>
```

### P2 / `app/(app)/integrations/page.tsx:143` · 集成卡片标题 `<b>` 应 `<h3>`
```tsx
<article ...>
  <b className="font-display text-sm">{i.name}</b>  ← 应当 <h3>
```

### P2 / `app/(app)/analytics/page.tsx:177` · 排行榜 `<b>` 当姓名容器
`<b>` 仅表字形粗。改 `<span className="block font-semibold">`。

### P2 / `app/(external)/share/[token]/page.tsx:69-82` · brand mark 重写
sidebar 已有 `<BrandMark />` 组件。share 可复用（或在 (external) 抽 `<ExternalHeader />`）。

---

## 维度六 · 中文文案

### pass · 整体合规
无「赋能 / 抓手 / 闭环」/ 无「您」/ 无感叹号 / 数字与单位间空格 ✓。

### P2 / `app/(app)/integrations/page.tsx:172` · 空态英文 id 泄漏
```tsx
没匹配到「{q || tab}」相关的集成。
```
`q=""`、`tab="connected"` 时渲染：

> 没匹配到「connected」相关的集成。

**改法**：
```tsx
const tabLabel = TABS.find((t) => t.id === tab)?.label ?? "全部";
没匹配到「{q || tabLabel}」相关的集成。
```

### P2 / `app/(external)/share/[token]/page.tsx:100` · `token {params.token}` 全串渲染
token 可能 32+ 字符撑爆窄屏。**改法**：`{params.token.slice(0, 6)}…` 或用 `ShieldCheck` icon 代替。

### P3 / `app/(app)/analytics/page.tsx:38` · `$` 未本地化
fixtures 是 USD，`$` 合适，但加 `USD` 后缀避免歧义。低优。

---

## 维度七 · 响应式

### pass · 主要断点
- 4 页 hero 全部 `flex flex-wrap items-end gap-4 md:gap-6` ✓
- KPI grid `grid-cols-2 lg:grid-cols-4` ✓
- analytics `<table>` 包 `overflow-x-auto` + `min-w-[520px]` ✓
- notifications 200px 侧栏 `md:grid-cols-[200px_1fr]` < 768 堆叠 ✓
- integrations 卡片 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` ✓
- share 双栏 `lg:grid-cols-[1.6fr_1fr]` ✓

### P2 / `app/(external)/share/[token]/page.tsx:90-93` · 「复制链接」< 480 也满文字
其它徽章已 `hidden md:flex`，复制按钮可同样 icon-only：
```tsx
<Button variant="outline" size="sm" onClick={copyLink}>
  {copied ? <Check /> : <Copy />}
  <span className="hidden sm:inline">{copied ? "已复制" : "复制链接"}</span>
</Button>
```

### P2 / `app/(app)/analytics/page.tsx:69-77` · 顶按钮组只第一个有 `aria-label`
其它按钮在 icon-only（< sm）模式下无 SR 名称。每个补：
```tsx
<Button variant="outline" aria-label="导出 CSV">
<Button aria-label="刷新数据">
```

### P2 / `app/(app)/notifications/page.tsx:117-124` · EmptyState 外 `py-16` 双层
EmptyState 自带 `px-6 py-14`，外层再 `py-16` < 480 占半屏。去掉外层 `py-16`。

### P3 / `app/(app)/integrations/page.tsx:100` · 顶部 tab 组 `ml-auto` 窄屏贴右
加 `justify-end md:justify-start`。

---

## 维度八 · 性能

### P1 / `app/(external)/share/[token]/page.tsx:1` · 整页 client（见维度二 P0）

### P2 / `app/(app)/notifications/page.tsx:1` · 整页 client
hero + sidebar 静态可拆 `<NotificationsHero />`（server）+ `<NotificationList />`（client）。

### P2 / `app/(app)/integrations/page.tsx:1` · 整页 client
hero 可 server。但 search + tab 都在 list 上面，拆得多反而复杂。低优。

### P2 / `app/(app)/analytics/page.tsx:48` · `await api.analytics()` 无缓存语义
analytics 是只读 7 天聚合，可 `next: { revalidate: 300 }`。当前 lib/api `cache: "no-store"`，每次打后端。

---

## 维度九 · 品牌一致

### P0 / `app/(external)/share/[token]/page.tsx:75,76,116-142` · 内联 SVG 7+ 处裸 hex
同文件出现：
- `#22D3B7`（line 75 stop, 132 fill, 134 text fill）
- `#38BDF8`（line 76 sky stop）
- `#15376a`（line 119 navy）
- `#050a18`（line 120 navy）
- `rgba(34,211,183,0.4 / 0.25 / 0.2)`（line 123, 124, 129, 131）
- `#F7F9FC`（line 137 text）
- `#8590A8`（line 140 graphite text）

v1 已经把 `<VideoPlayer />` 抽出后违规集中到一处，share 又复制一遍，违规放大。**改法**：见维度三 P1，复用 `<VideoPlayer />` + 把 hex 抽 `lib/theme.ts`（refine 002 待办里已有该项）。

### P1 / `app/(app)/integrations/page.tsx:24-39` · 外部品牌色 `i.color` 合理 ✓ 但部分太暗
Slack `#4A154B`、YouTube `#FF0000`、LinkedIn `#0A66C2` 是外部公司官方品牌色 ✓。
但 Notion `#0f0f0f`、TikTok `#000000` 在深色背景上几乎不可见。加 `border border-white/10` 描边。

### P2 · 其它颜色一致 ✓
notifications `KIND_ICON` 颜色（done=accent / info=sky / warn=amber / fail=rose / mention=violet / billing=graphite）与 v1 status-badge / badge variants 对齐 ✓。analytics 进度条渐变 `from-accent-500 to-sky-400` 与 KpiTile sparkline 一致 ✓。

---

## 维度十 · 跨页面一致

### pass · hero 模式
4 个新页全部继承 v1 hero：eyebrow（`text-[11px] uppercase tracking-[0.16em] text-accent-300`）+ h1（`font-display text-[28px] md:text-[34px]`）+ p（`max-w-prose text-sm text-muted-foreground`）+ 右侧按钮组 ✓。

### warn · share/[token] 走两套
(external)/layout 只包 `<div className="min-h-screen">`，share 自己实现 header / footer / 容器宽度。未来加 `/login`、`/status` 又会重写。**建议**：在 `components/external/` 抽 `<ExternalHeader />` `<ExternalFooter />`。

### warn · loading / not-found / error 都还在 root
- `app/loading.tsx`（`grid-cols-2 lg:grid-cols-4`）带 KPI skel，share 触发 loading 时风格完全不匹配
- `app/not-found.tsx` 跳「返回工作台 / 项目库」，对外部访客无意义

**改法**：(app) 和 (external) 各自加 loading/error/not-found；root 保留为 fallback 或删。

### P2 · 按钮 icon 大小不齐
analytics 三个按钮都 `h-3.5 w-3.5`（同 dashboard / topbar）但 dashboard `<Sparkles className="h-4 w-4">` 又是 4。cva `[&_svg]:size-4` 已经管，所有 `<icon>` 都不该手写尺寸。后续 ring 收口。

---

## 特殊检查项

### A. (external)/share/[token] 不能引导任何 sidebar / 不调任何要授权的 API

| 检查 | 结果 |
|---|---|
| (external)/layout.tsx 是否带 sidebar | **OK**（不带） |
| share page 是否 import `api` 或 sidebar / topbar | **OK** |
| brand logo `<Link href="/">` 跳转 | **warn** — `/` redirect → `/dashboard` 外部访客踩入 (app) |
| footer "了解 ShadowBlade" `<Link href="/">` | **warn** — 同上 |
| 引导「在编辑器中打开」类按钮 | **OK**（无） |

**改法**：root `app/page.tsx` 判断未登录走 marketing 页；或 brand logo 改 `<Link href="https://shadowblade.io/">` 外链。

### B. analytics 柱图 `maxRendered` 抗 0 / 抗负

`app/(app)/analytics/page.tsx:49 const maxRendered = Math.max(...a.timeseries.map(d => d.rendered));`

| 边界 | 结果 |
|---|---|
| 非空、有正值 | OK |
| 空数组 `[]` | `Math.max()` → `-Infinity` → `value / -Infinity = -0` → height 0 ✓ |
| 全 0 | `0/0 = NaN` → CSS 忽略 → height 0 ✓ |
| 含负值（不应发生） | 比例为负 → CSS 忽略 |

视觉不破，但 SR 读「通过 NaN」很丑。**改法**：`Math.max(1, ...a.timeseries.map(d => d.rendered))`。

### C. notifications dismissed Set 过期 bug

| 场景 | 结果 |
|---|---|
| 点「全部标已读」 | `dismissed = Set(all ids)`，visible 变空，触发 EmptyState（语义错位，见维度二 P1）|
| TABS 计数 | **bug** — 模块级 hardcode `NOTICES.length`，永远 8，从不更新 |
| 切 tab 后再点「全部标已读」 | 仍 dismiss 全部 |
| 刷新页面 | dismissed 重置（无持久化），通知重现 |

### D. integrations search q + tab 正交性 — **bug 确认存在**

`page.tsx:57-61`：
```ts
const list = INTEGRATIONS.filter((i) => {
  if (tab === "connected") return i.connected;       // ← BUG：直接 return，吞掉 q
  if (tab !== "all" && i.cat !== tab) return false;
  return !q || ...;
});
```

| tab | q | 实际 | 期望 |
|---|---|---|---|
| `all` | `""` | 全部 15 ✓ | ✓ |
| `comms` | `"notion"` | 0（comms 里无 notion） ✓ | ✓ |
| `connected` | `""` | 已连接 6 ✓ | ✓ |
| **`connected`** | **`"slack"`** | **6（q 被忽略）** | **1** |

**改法**：
```ts
const list = INTEGRATIONS.filter((i) => {
  if (tab === "connected" && !i.connected) return false;
  if (tab !== "all" && tab !== "connected" && i.cat !== tab) return false;
  if (!q) return true;
  const needle = q.toLowerCase();
  return i.name.toLowerCase().includes(needle) || i.desc.toLowerCase().includes(needle);
});
```

### E. root layout 瘦身 — metadata 检查

`app/layout.tsx`：`title` ✓ / `description` ✓ / `icons` ✓ / `openGraph.images` ✓。

**缺**：
- `metadataBase` — 缺失会让 build warn `metadata.metadataBase is not set for resolving social open graph or twitter images`；OG image 是相对路径 `/og-image.svg`
- `openGraph.title` / `description`（可回退 ✓）
- `twitter`
- share/[token] 没有 `generateMetadata` 覆盖，link unfurl 全都显示同一句 — 对分享链接是品牌损失

**改法**：root 加 `metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://shadowblade.io")`；share/[token] 加 `generateMetadata` 输出 `Ava Chen 邀请你审阅 — 智能腕环 v17`。

---

## Refine 待办队列（按优先级排序）

### P0（必修 — 功能 / a11y / 安全）
1. **`integrations:57-61` search + tab 不正交** — "已连接" tab 下 `q` 被吞；按 D 改三段式 filter
2. **`share/[token]:150-161 + 163-171` 双 aria-label 重复 v1 已修 bug** — 复用 `<VideoPlayer />`（一次解决 P0.2 + P1.5 + P0.7）
3. **`analytics:116-117` 柱图 `<div aria-label>` SR 不读** — 加 `role="img"` 或包 `<figure>` + sr-only 表

### P1（影响质量 / 性能）
4. **`share/[token]:1` 整页 client 299 行** — page 退 server，4 个交互各抽小 client
5. **`notifications:65,82` "标已读" 实为 dismiss** — 分 `read` / `dismissed` 两 state，按钮文案对齐
6. **`notifications:45-52` TABS 计数不更新** — `useMemo(() => ..., [dismissed])` 重算
7. **`share/[token]:113-184` 内联 SVG 大量裸 hex** — 同 P0.2，复用 `<VideoPlayer />`
8. **`integrations:7` `Input` import 未用** — 删或改用
9. **`integrations:128-129` `transition-colors` + `transition-all` 冲突** — 删 line 128 的
10. **`notifications:151` / `share/[token]:172,176,251` `<time>` 缺 dateTime** — 加 ISO 字段或改 `<span>`
11. **`analytics:49` `maxRendered` 不抗 0** — `Math.max(1, ...)`
12. **`app/loading.tsx` / `not-found.tsx` 未跟随 route group 拆** — (external) 各加 boundary
13. **`app/page.tsx` redirect 让外部访客踩进 (app)** — 判断登录 / brand logo 改外链
14. **root layout 缺 `metadataBase`** — 加，避免 build warn + 让 share OG image 生效

### P2（细节 / 类型 / 语义）
15. **`analytics:29` `KIND_CLASS: Record<string,string>`** — 拆 `DriftKind` 联合
16. **`analytics:35` `formatKpi(label)` 不用** — 删参数
17. **`integrations:116` `as "all" | "connected"` 逃逸** — 抽守卫 + counts 类型化
18. **`notifications:54` `typeof Check` → `LucideIcon`** — 统一
19. **`notifications:31` actions key 用 label 可能重复** — 加 id 或 index
20. **`analytics:163` `<table>` 缺 `<caption sr-only>`** — 加
21. **`integrations:172` 空态英文 id 泄漏** — `tabLabel`
22. **`share/[token]:100` `token` 全串显示** — `slice(0, 6) + "…"`
23. **`analytics:69-77` 顶按钮 icon-only 缺 aria-label** — 每个补
24. **`notifications:141 / integrations:143` `<div>` / `<b>` 应 `<h3>`** — 调
25. **`analytics:177` `<b>` 当姓名** — 改 `<span>`
26. **`share/[token]:46-53` clipboard 静默失败** — 加错误反馈
27. **`share/[token]:51` `setTimeout` 无 cleanup** — useEffect + ref
28. **`integrations:24-39` 外部品牌色 `#000000` / `#0f0f0f` 在深色不可见** — `border border-white/10`
29. **`notifications:117-124` EmptyState 外 `py-16` 双层** — 去外层
30. **`integrations:100` 顶 tab 组 `ml-auto` 窄屏贴右** — `justify-end md:justify-start`
31. **(external) 抽 `<ExternalHeader />` `<ExternalFooter />`** — 为 /login /status 准备
32. **`api.analytics()` 加 `revalidate: 300`** — 省一次后端调用

### P3（架构 / token 收口）
33. **`bg-accent-500/[0.022]` 等极小任意值** — 收 token
34. **按钮 icon `h-3.5 w-3.5` vs `h-4 w-4` 不齐** — 删手写尺寸，全靠 cva `[&_svg]:size-4`
35. **share/[token] 升 Next 15 时 `params: Promise<...>`** — 留 TODO

---

## 总体观感

- **Design v2 视觉延展非常稳**：4 新页都精确复制 v1 hero（eyebrow + h1 + p + 右按钮组），KPI / Card / Badge 用法对得上；route group 重组干净（root 瘦身 + (app) 接 sidebar + (external) 裸壳）。
- **share/[token] 是本轮最大债务**：299 行整页 client + 内联 SVG 一锅端 + 双按钮 a11y bug 全部是 v1 已修过的回归。**直接复用 `<VideoPlayer />` 能一次解决 3 个 P0/P1**。
- **integrations 有一个真实功能 bug**（search 在 connected tab 失效），不修上线用户分类页搜不到东西。
- **notifications 有一个语义 bug**（"标已读" 实为 dismiss），不影响功能但让用户困惑。
- **analytics 是 4 页里质量最高的**，唯一 P0 是柱图 SR 可读性。
- **route group 重组本身 pass**，但 loading / not-found / error 没跟着拆是遗留。

修完 P0 共 3 项 + P1 共 11 项后，4 页可发 v2 internal beta；P2 在 refine 003 处理。
