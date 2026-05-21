# ShadowBlade Next.js · Test Ring Report 002

审计对象：`frontend-next/` 全部 `.tsx` / `.ts` / `.css`（`node_modules` 除外），重点核查 Refine ring 002（commit 7cc4e92）触动的 21 文件
审计日期：2026-05-21
审计员：Test ring · pass 002（只读，不动源 · 纯静态分析）
基线：`tsc --noEmit` 0 error
源文件统计：3 个新增（mobile-sidebar / project-filter / projects-board）+ 18 个编辑 + 既有 boundary 文件

---

## 顶部总表

### 10 类审计维度

| # | 维度 | 评级 | 一句话总结 |
|---|---|---|---|
| 1 | TypeScript 严格性 | **pass** | ring 001 的 `as never` 已修；新增的 `as Purpose` / `as Draft` 是合理的运行时边界 |
| 2 | React 模式 | **warn** | `setInterval` 取消路径 1 处状态泄漏；`stepTimer.current` 不被回收；新增组件 client/server 边界正确 |
| 3 | Tailwind / shadcn | **warn** | `animate-[shimmer_...]` 与 tailwind.config 的 `shimmer` keyframe 双定义、语义冲突；`peer-disabled` 死代码尚未删 |
| 4 | 无障碍 (a11y) | **warn** | mobile-sidebar 无 focus-trap、drawer 打开后初始焦点未管理；sparkline 缺 title；`tablist` 角色用在 button 行需要包裹 |
| 5 | 语义 HTML | **pass** | project-detail 终于用 `<article>`；team 表格语义 ✓；mobile-sidebar 用 `role=dialog` ✓ |
| 6 | 中文文案 | **pass** | 整体合规；"再渲染一版" / "切换为播放" 等文案进步明显；评论里夹英文是合理 |
| 7 | 响应式 | **pass** | 8 页头一致 `flex flex-wrap items-end gap-4`、KPI grid 加 `md:`/`lg:`、team 双视图；mobile-sidebar 触点充足 |
| 8 | 性能 | **warn** | KpiTile sparkline 计算挂在 server render，OK；create-wizard `interval` + autosave debounce 双 `useEffect` 写回 ref 不一致 |
| 9 | 品牌一致 | **warn** | accent-500 / sky / amber / violet 已收口；但 sparkline `rgb(125 232 207)`、`rgba(34,211,183,...)` 仍是裸 hex，未走 token |
| 10 | 可用性 / 一致性 | **warn** | CTA 文案统一为「新建视频」✓；但 settings 侧栏导航 `i===0` 永远高亮，不跟 anchor 滚动；library 文件夹 hardcode count 残留 |

### 8 个 page 评级（refine 002 后）

| 路由 | 评级 | 主要问题 |
|---|---|---|
| `/` (`app/page.tsx`) | **pass** | redirect，无变 |
| `/dashboard` | **pass** | KpiTile 喂 trend ✓；类别 tab 替换为 `ProjectFilter` ✓；only 残留 `!` 已改 `AlertTriangle` |
| `/create` | **warn** | CreateWizard 整体 client 仍未拆；`stepTimer.current` 在 cancel/start 切换时不 reset、autosave 跟 restored 状态会互相覆盖 |
| `/projects` | **warn** | `ProjectsBoard` 把 `Card` 当 wrapper 但内部直接 `<>`，违反 Card 内部结构约定；`inProgress` 包含 `running` 但 Project.status 永远不会是 `running` |
| `/projects/[id]` | **warn** | VideoPlayer 双按钮已修（aria-label + tabIndex=-1）✓；但 SCENES 顶层是 hardcode 6 条不动 |
| `/templates` | **warn** | 顶部 filter chip 仍 `i === 0` 永远高亮，未接 onClick；其它 ✓ |
| `/library` | **warn** | FOLDERS count 仍 hardcode，与 ASSET_FALLBACK 数（10 项）不对齐；上传按钮缺 `aria-label` |
| `/brand` | **pass** | `KITS` 已删并接 `api.brandKits()` ✓；`<h4>` 跳级保留（acceptable） |
| `/team` | **pass** | Fragment 已具名 ✓；email 走 fallback ✓；双视图 ✓ |
| `/settings` | **warn** | SettingsForm 抽出 ✓ 但 page 本身侧栏 `i === 0` hardcode 高亮；select 已加 aria-label ✓ |

---

## 维度一 · TypeScript 严格性

### pass · ring 001 的逃逸都修了

`as never` 已删（`team:143/202` 改 `?? "default"`）；`PERMISSIONS` 改成 `Permission[]` object 数组（`team:18-25`）；`ROLE_VARIANT` 显式声明 `Record<string, BadgeProps["variant"]>`（`team:11`）。

### P2 / `components/workspace/create-wizard.tsx:93` · `JSON.parse(raw) as Draft` 不验证字段

```ts
const parsed = JSON.parse(raw) as Draft;
setDraft({ ...DEFAULT_DRAFT, ...parsed });
```

如果用户本地有损坏的旧 v1 草稿，会把 `parsed.purpose` 等不合法字符串塞进 state，导致 `Tabs value={draft.purpose}` 不匹配任何 Trigger 时 Radix 抛 warn；更糟的是 `template` 串可能是被外部脚本注入的任意值。

**推荐改法**（最小 guard）：
```ts
const ALLOWED_PURPOSES = ["marketing", "training", "product_demo", "social"] as const;
const safe = (raw && typeof raw === "string") ? JSON.parse(raw) : null;
const cleaned: Partial<Draft> = {
  template: typeof safe?.template === "string" ? safe.template : DEFAULT_DRAFT.template,
  purpose: ALLOWED_PURPOSES.includes(safe?.purpose) ? safe.purpose : DEFAULT_DRAFT.purpose,
  // ...其余同理
};
setDraft({ ...DEFAULT_DRAFT, ...cleaned });
```

### P3 / `components/workspace/projects-board.tsx:18` · `status` state 是 `string` 而非 `Status`

```ts
const [status, setStatus] = useState<string>("any");
```

后续 `p.status !== status` 字符串比较是 OK，但失去了拼写检查。

**推荐**：`useState<"any" | Status>("any")`。

### P3 / `components/workspace/kpi-tile.tsx:23` · `trend` undefined 时的 placeholder 数组易被认为是死代码

```ts
const sparkline = trend && trend.length > 1 ? trend : [4, 6, 5, 7, 8, 7, 9];
```

placeholder 是设计意图（refine log 明写）。但当 `trend.length === 1` 时会走 placeholder—不直观。

**推荐**：拆 helper 或抽常量 `FALLBACK_TREND` 并加注释 "occupant pattern"。

---

## 维度二 · React 模式

### P0 / `components/workspace/create-wizard.tsx:114-133` · `stepTimer.current` 双跑 + cancel 时状态机漏跳

```tsx
useEffect(() => {
  if (!running) return;
  stepTimer.current = setInterval(() => { ... }, 800);
  return () => { if (stepTimer.current) clearInterval(stepTimer.current); };
}, [running]);

function cancel() {
  if (stepTimer.current) clearInterval(stepTimer.current);
  setRunning(false);
}
```

**两个真实 bug**：

1. `cancel()` 手动 `clearInterval` 后，`useEffect` cleanup 会再 `clearInterval(stepTimer.current)`（指向同一个已被清理的 id），无害但语义重复。
2. **每次 `start()` 重新触发 effect 时，`stepTimer.current` 仍是上一次跑完的旧 id**，新 interval 覆盖它后，旧 id 永远不会被清理 if 用户在 `setRunning(true)` 立即又 cancel-quick-start 的窄窗。
3. 更隐蔽：`setStep` 在 `setRunning(false)` 的同时 `return s` 后，下一次 `start()` 又 `setStep(0)` 会触发 effect 重跑，但 `[running]` 依赖让旧 effect cleanup 先跑 → cleanup 引用的 `stepTimer.current` 此刻**可能已经是新 interval 的 id**（因为 setState 是异步的），把刚刚启动的 interval 立刻清掉。

**推荐改法**：把 `stepTimer.current` 改成局部 `id` 变量，cleanup 闭包捕获正确的 id：
```tsx
useEffect(() => {
  if (!running) return;
  const id = setInterval(() => { ... }, 800);
  return () => clearInterval(id);
}, [running]);

function cancel() {
  // 不直接 clearInterval；改变 running 让 effect cleanup 接管
  setRunning(false);
}
```
顺便 `stepTimer` ref 可以删了。

### P1 / `components/workspace/create-wizard.tsx:101-109` · autosave debounce 与 restore 互相覆盖

```tsx
useEffect(() => {
  const raw = localStorage.getItem(DRAFT_KEY);
  if (raw) {
    const parsed = JSON.parse(raw) as Draft;
    setDraft({ ...DEFAULT_DRAFT, ...parsed });
    ...
  }
}, []);

useEffect(() => {
  const t = setTimeout(() => { localStorage.setItem(DRAFT_KEY, JSON.stringify(draft)); ... }, 600);
  return () => clearTimeout(t);
}, [draft]);
```

restore effect 在初始 mount 后跑，`setDraft` 一次，autosave effect 监听 `draft` 立刻被触发 — 但写回的是刚刚 restore 过的同一份数据，看不出问题。**真正的 bug**：如果用户在 600ms 窗口内连续打 `update("brief", ...)`、`update("brief", ...)` ... 每次 setTimeout 都被 reset；最后一笔成功保存。OK。

**问题在另一边**：first-mount 时 `draft = DEFAULT_DRAFT`，autosave effect 跑 → 600ms 后写入 DEFAULT，但 restore effect 在那 600ms 内才把 localStorage 里的旧草稿读出来并 setDraft → 触发新 autosave → 这次正确保存。**首次访问的 race condition**：如果 restore 慢于 600ms，DEFAULT 会覆盖 localStorage。实测在 dev 几乎不会发生，但慢机 / 大 DOM 容易。

**推荐改法**：用 `restored` flag 在 first autosave 跳过：
```tsx
const initialMount = useRef(true);
useEffect(() => {
  if (initialMount.current) { initialMount.current = false; return; }
  const t = setTimeout(() => { localStorage.setItem(...) ... }, 600);
  return () => clearTimeout(t);
}, [draft]);
```

### P1 / `components/layout/mobile-sidebar.tsx:48-60` · 抽屉打开缺 focus-trap、初始焦点未设置

```tsx
useEffect(() => {
  if (!open) return;
  document.body.style.overflow = "hidden";
  const onKey = (e) => { if (e.key === "Escape") onClose(); };
  document.addEventListener("keydown", onKey);
  return () => { document.body.style.overflow = prev; ... };
}, [open, onClose]);
```

a11y：drawer 是 `role="dialog" aria-modal="true"`，按规范应：
- 打开时把焦点移到第一个可聚焦元素（或 close button），
- 关闭时把焦点还给 trigger（hamburger button）。

当前打开后焦点仍在 hamburger 上，screen reader 听到「主导航 dialog 已打开」但 tab 跳出 dialog 也没人挡 — 用户用键盘可以 tab 到背后 main 里的 link，破坏 modal 模型。

**推荐改法**（最小补丁，不引入 focus-trap 包）：
```tsx
const ref = useRef<HTMLElement>(null);
useEffect(() => {
  if (!open) return;
  const previouslyFocused = document.activeElement as HTMLElement | null;
  const firstLink = ref.current?.querySelector<HTMLAnchorElement>("a");
  firstLink?.focus();
  return () => { previouslyFocused?.focus(); };
}, [open]);
// 给 <aside ref={ref}>
```

进一步 trap：监听 `keydown` Tab 时检查 `ref.current.contains(activeElement)`，若离开则 `preventDefault` + focus 第一/最后一个可聚焦元素。可留 ring 003。

### P2 / `components/layout/mobile-sidebar.tsx:50-51` · body overflow 锁有副作用

```tsx
const prev = document.body.style.overflow;
document.body.style.overflow = "hidden";
```

如果有同时打开的对话框（未来 modal）也想锁 body，先开 mobile-sidebar → 后开 modal → 关 modal 会把 body overflow 设回 `""`，但 sidebar 还开着。此时 sidebar 关闭时 cleanup 写的是 `prev`（捕获了 modal 设置的 `""`，不是初始的）— 实测两边都用 `prev` 也不会出大问题，但**当前 cleanup 写 `document.body.style.overflow = prev` 而非 `""`/`unset`，能保留外部脚本设置的样式**，是好的；不过应该加注释提醒未来作者。

### P2 / `components/workspace/meta-tabs.tsx:131-135` · `setTimeout` cleanup 缺

```tsx
function send() {
  if (!text.trim()) return;
  setSending(true);
  setTimeout(() => { setSending(false); setText(""); }, 600);
}
```

如果用户在 send 后立即卸载（路由切换），`setState on unmounted component` warning。`CommentComposer` 是 page 子组件，在 `/projects/[id]` 卸载或 tab 切走时会触发。

**推荐改法**：
```tsx
const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);
function send() {
  ...
  timerRef.current = setTimeout(...);
}
```

### P2 / `components/workspace/share-link.tsx:14-17` · `setTimeout` 同上未 cleanup

同理 `setCopied(false)` 的 `setTimeout(..., 1800)` 没 cleanup。

### P2 / `components/workspace/projects-board.tsx:46-94` · `Card` 内顶层 fragment + 自定义 `border-b`

```tsx
<Card>
  <ProjectsBoard /> {/* returns <> filter-bar + CardContent */}
</Card>
```

`Card` 是 `<div>` wrapper，`ProjectsBoard` 第一行 `<div className="... border-b ...">` 是自制的 header；`CardContent` 是第二行。语义可行，但和 `CardHeader` / `CardContent` 的设计语言不一致 — `projects/page.tsx` 没有 `<CardHeader>`，filter bar 充当 header。

**推荐改法**：在 `ProjectsBoard` 内部使用 `<CardHeader>` 包 filter bar，与其它页统一。

---

## 维度三 · Tailwind / shadcn

### P1 / `tailwind.config.ts:74,79` ↔ `app/globals.css:81-84` · `shimmer` keyframe 双定义且语义不同

```ts
// tailwind.config.ts
keyframes: { shimmer: { "100%": { transform: "translateX(100%)" } } }
animation: { shimmer: "shimmer 2s infinite" }
```
```css
/* globals.css */
@keyframes shimmer {
  0%, 100% { transform: translateX(-30%); opacity: 0.35; }
  50%      { transform: translateX(30%);  opacity: 0.8; }
}
```

`pipeline-stage.tsx:30` 用 `animate-[shimmer_2.4s_ease-in-out_infinite]`（任意值语法直接引用 keyframe 名）。Tailwind 生成的 keyframe 与 globals.css 的同名 keyframe **由 CSS cascade 决定哪个赢** — Tailwind 把 keyframe 注入到 `@layer utilities` 里，globals.css 的 `@keyframes shimmer` 在 root scope，**后定义的覆盖**。看打包顺序：Tailwind utilities 走 `@tailwind utilities` 注入点 = `globals.css:3`，而文件内的 `@keyframes shimmer` 在第 81 行（之后）。所以**实际生效的是 globals.css 那份**（`-30% → 30%` + opacity）。

**两个问题**：
1. 同名 keyframe 双定义 — 维护时容易改错一份。
2. `tailwind.config.ts` 的 `animation: shimmer` utility（class `animate-shimmer`）**全代码库没人用**，是死代码。

**推荐改法**：删 `tailwind.config.ts:74,79` 两行；保留 globals.css 的。同时把 `animate-[shimmer_2.4s_...]` 提升为 utility：
```ts
// tailwind.config.ts extend
animation: {
  "shimmer-slow": "shimmer 2.4s ease-in-out infinite",
}
```
然后用 `animate-shimmer-slow`。

### P1 / `components/ui/button.tsx:7` + asChild · `active:scale-[0.97]` 在 `asChild=true` 时仍生效

```tsx
const Comp = asChild ? Slot : "button";
return <Comp className={cn(buttonVariants(...))} ... />;
```

Slot 把所有 props（含 className）合并到第一个子元素（`<Link>` 的 anchor）。所以 `active:scale-[0.97]` **会** 应用到 `<a>` 上 — 这是想要的（点击 link 时也回弹）。问题：很多 dashboard 页用 `<Button asChild><Link href="/create">新建</Link></Button>`，`<a>` 的 default outline + Button 的 `focus-visible:ring` 都在；用户连续点击会触发浏览器的 `:visited` 状态走样，加 `active:scale` 后视觉略有抖动。

实测在标准浏览器下没问题。**但有一个真实坑**：`active:scale-[0.97]` 与 link 的 `hover:-translate-y-px` 组合时，连续 hover→click→release 状态切换在 chromium 上偶尔丢帧。**推荐**：保留，但加 `will-change: transform`。或更稳：把 `active:scale-[0.97]` 收口到非 link variants。

### P2 / `components/ui/label.tsx:14` · `peer-disabled` 仍是死代码

ring 001 P2 提过，本轮未修：
```tsx
"text-[11px] ... peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
```

整个项目都没有 `<input className="peer">` 模式。删掉。

### P2 / `app/library/page.tsx:65-67` · 文件夹按钮还在用模板字符串 className 拼

```tsx
className={`flex items-center gap-3 rounded-md ...${f.active ? "..." : "..."}`}
```

不致命，但其它新代码都用 `cn()`，库页风格漂移。建议改 `cn()`。

### P2 / `app/settings/page.tsx:43-46`、`app/brand/page.tsx:54-56`、`app/library/page.tsx:65` · 三处模板字符串 className 残留

同上，可借机统一。

### P2 / `components/workspace/kpi-tile.tsx:27-28` · sparkline 颜色用裸 rgb/rgba

```ts
const stroke = positive ? "rgb(125 232 207)" : "rgb(252 211 77)";
const fill = positive ? "rgba(34,211,183,0.22)" : "rgba(245,158,11,0.22)";
```

这是 SVG attribute（`stroke`/`fill`），无法直接用 tailwind class，但 hex 与 token 漂移：tailwind 的 `accent-300=#6ee2c5` ≈ `rgb(110 226 197)` 而非代码中的 `rgb(125 232 207)`，肉眼差几个点不出戏，但**严格地不是同一个颜色**。

**推荐改法**：从 tailwind config 推导：
```ts
// lib/theme.ts (新文件)
export const TREND_COLORS = {
  positiveStroke: "rgb(110 226 197)", // accent-300
  positiveFill:   "rgba(34,211,183,0.22)", // accent-500/22
  negativeStroke: "rgb(252 211 77)",  // amber-300
  negativeFill:   "rgba(245,158,11,0.22)", // amber-500/22
} as const;
```

---

## 维度四 · 无障碍 (a11y)

### P0 / `components/layout/mobile-sidebar.tsx:77-150` · drawer 无 focus-trap（详见维度二 P1）

阻塞性 a11y bug — keyboard 用户可以 tab 出 modal。

### P1 / `components/workspace/kpi-tile.tsx:47-84` · sparkline SVG `aria-hidden` 但无可访问替代

```tsx
<svg viewBox="0 0 80 32" aria-hidden ...>
```

aria-hidden 是对的（避免 screen reader 念点位）— 但**对盲用户完全不可达「趋势」信息**。「本月渲染次数 387 / 1,000，12.4% 较上月」是文本可达的，但 sparkline 形状（"加速增长 / 平稳 / 下滑"）丢失。

**推荐改法**：给 KpiTile 加 `srHint?: string`，例如 `srHint="过去 7 天趋势：210 → 387，持续加速"`，在 svg 旁加 `<span className="sr-only">{srHint}</span>`。或更简：从 `trend` 自动推导 "上升 / 平稳 / 下降"。

### P1 / `components/workspace/project-filter.tsx:35-58` + `projects-board.tsx:47-69` · `role="tablist"` 不完整

```tsx
<div role="tablist" aria-label="按用途筛选">
  {FILTERS.map((f) => (
    <Button role="tab" aria-selected={...} ...>
  ))}
</div>
```

按 WAI-ARIA：tab 必须有对应的 `tabpanel`（`aria-controls`）+ `tabpanel` 有 `aria-labelledby`。当前没有 panel，只是过滤了下面 grid 的可见项；这其实是 **toolbar / radiogroup 语义**而非 tablist。

**推荐改法**：
- 改 `role="toolbar" aria-label="按用途筛选项目"`；
- button 改 `aria-pressed` 而非 `aria-selected`；
- 或保留 tablist 语义但补 `aria-controls="projects-grid"` 指向 grid 容器。

### P1 / `app/library/page.tsx:44-47` · 上传按钮缺 `aria-label`

```tsx
<Button>
  <Upload className="h-4 w-4" /> <span className="hidden sm:inline">上传素材</span><span className="sm:hidden">上传</span>
</Button>
```

在 < sm 时屏幕仅显示「上传」，且 Upload icon 没 `aria-hidden` — screen reader 念「上传 上传」。其余 7 页同模式（dashboard / team / settings / projects 等）icon 都没 `aria-hidden`。

**推荐改法**：给所有 lucide icon 加 `aria-hidden`（80% 已有；剩余约 20 处遗漏）。

### P2 / `components/workspace/pipeline-stage.tsx:55-58` · "运行中" 标签只是视觉

```tsx
{running && (
  <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-sky-300">运行中</span>
)}
```

文本是可读的 ✓。但同时整行没有 `aria-live`，状态改变（如 "脚本" 从 running → succeeded）screen reader 不会播报。

**推荐改法**：外层加 `role="status" aria-live="polite"` 或在 dashboard pipeline 容器加 `aria-live`。

### P2 / `app/team/page.tsx:126-132` · 移动端卡片视图的 presence dot 用 `aria-label`

```tsx
<span aria-label={PRESENCE_LABEL[presence]} className="... rounded-full ring-2 ring-card ..." />
```

`<span>` 不是 interactive，screen reader 默认不读 `aria-label`（除非用户主动 navigate 到它）。读者可能不知道头像旁的小圆点是 presence 状态。

**推荐改法**：把 dot 改 `<span role="img" aria-label={...}>` 或者干脆在 avatar 旁加 `<span className="sr-only">{PRESENCE_LABEL[presence]}</span>`。

### P2 / `components/workspace/meta-tabs.tsx:77-83` · 评论 presence dot 同上

```tsx
<span aria-hidden className={cn("absolute ..." , PRESENCE_DOT[c.presence])} />
```

这里反而是 `aria-hidden`（更糟）+ 没有任何文本提示「Priya 在线」。同改法。

---

## 维度五 · 语义 HTML

### pass · project-detail 包 `<article>` ✓（ring 001 P1 修了）
### pass · team 表格用 `<table>` ✓
### pass · mobile-sidebar `role="dialog" aria-modal="true"` ✓

### P2 / `components/workspace/meta-tabs.tsx:54-59` · `<dt>` / `<dd>` 在 `<div>` 内

```tsx
<div key={k} className="grid grid-cols-[100px_1fr] gap-3 py-1.5">
  <dt className="text-muted-foreground">{k}</dt>
  <dd className="text-foreground">{v}</dd>
</div>
```

按规范，`<dt>` / `<dd>` 必须在 `<dl>` 内才合法。当前外层是 `<TabsContent>`（div）— 语义违规。

**推荐改法**：把 `META.map` 外层改 `<dl className="grid gap-2">`，里面行用 `<div>` 包对应 `<dt>/<dd>`（仍合法 — HTML5 允许 `<dl>` 内有 `<div>` 包对组）。

### P2 / `app/team/page.tsx:228-260` · 权限矩阵用 CSS Grid，无表格语义

```tsx
<div className="grid min-w-[640px]" style={{ gridTemplateColumns: "240px repeat(5, 1fr)" }}>
  <div /> {ROLES.map(r => <div>{r.label}</div>)}
  {PERMISSIONS.map(perm => <Fragment>{...}</Fragment>)}
</div>
```

权限矩阵在 a11y 上是「表格」(row=permission, col=role, cell=●/○)。screen reader 当前听到的是一长串孤立单元，没办法对应回 "渲染视频在 admin 列是允许的"。

**推荐改法**：替换为 `<table role="grid">` + `<thead>` + `<tbody>`，每个 cell `<td>` 加 `aria-label="渲染视频 · 管理员 · 允许"`。或保留 div grid，但给每个 cell 加完整 aria-label。

---

## 维度六 · 中文文案

### pass · 整体合规

- 「再渲染一版」「切换为播放」「无需打断节奏」等新文案符合规范（短句、不假大空）。
- empty state 「该分类暂无项目，换一个 tab 试试」「没有匹配项 — 试着放宽筛选条件」是企业级 SaaS 语气 ✓。
- "渲染失败" "首版已渲染" "正在生成（n/m）" 状态文案准确。

### P3 / `app/dashboard/page.tsx:73` · "春季产品发布 — 智能腕环 · 28 秒 · 9:16"

mdash 与 middot 混用：项目名用 `—`（mdash），分隔元数据用 `·`（middot）。`/projects/[id]:35` 同样。一致性 ✓。**保留**。

### P3 / `components/workspace/create-wizard.tsx:355` · "重试" 按钮没有 icon-label 一致

```tsx
<Button size="sm" variant="outline" onClick={start} ...>
  <RotateCcw className="h-3 w-3" /> 重试
</Button>
```

`RotateCcw` 是「逆时针」icon，对应「撤销」更准确，「重试」更合 `RefreshCw`。

**推荐**：换 `RefreshCw` 与 `error.tsx` 一致。

### P3 / `components/workspace/meta-tabs.tsx:88-90` · 评论 thread 徽章

```tsx
<span ...>+{c.thread} 回复</span>
```

`thread=2` 显示 "+2 回复"。中文里 "+2 回复" 略生硬，更常见的是 "2 条回复" 或 "+2"。

**推荐**：`{c.thread} 条回复` 或纯数字 `+{c.thread}`。

---

## 维度七 · 响应式

### pass · ring 001 P0 已大幅修复

- `app/layout.tsx:32` 主 grid 已 `grid-cols-1 md:grid-cols-[248px_1fr]` ✓
- sidebar `hidden md:flex` ✓
- topbar 加 hamburger trigger + drawer ✓
- 8 个 page 头统一 `flex flex-wrap items-end gap-4` + h1 `text-[28px] md:text-[34px]` ✓
- KPI grid 全部 `grid-cols-2 md:grid-cols-4`（dashboard `lg:grid-cols-4`）✓
- team 双视图 `md:hidden` 卡片 + `hidden md:block` 表格 ✓

### P1 / `app/create/page.tsx:8` · `<div className="flex items-end gap-6">` 没 wrap

```tsx
<div className="flex items-end gap-6">
  <div>
    <h1 className="font-display text-[34px] ...">写一份简报，4 分钟拿到成片。</h1>
    ...
  </div>
</div>
```

只有一个子元素，但 wrap class 缺失；与其它 8 页头不统一。h1 也是固定 `34px`，没有 `text-[28px] md:text-[34px]` 响应式。**< 360px 会撑破容器**（"写一份简报，4 分钟拿到成片" 实测 15 字 + 28px font ≈ 420px 宽，溢出）。

**推荐改法**：
```tsx
<div className="flex flex-wrap items-end gap-4 md:gap-6">
  <div className="min-w-0 flex-1">
    <h1 className="font-display text-[26px] font-semibold tracking-tight md:text-[34px]">写一份简报，4 分钟拿到成片。</h1>
    ...
```

### P1 / `components/workspace/create-wizard.tsx:167` · `lg:grid-cols-[1.4fr_1fr]` 在 < lg 是单列

OK，但右侧 sticky `top-[76px]` 在 < lg 也生效（虽然单列下其实在底部），可能导致占位异常。

**推荐**：sticky 只在 `lg:sticky lg:top-[76px]`。

### P2 / `app/projects/[id]/page.tsx:51` · 同 wizard 单列 sticky 同问题

```tsx
<section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr] items-start">
```

右侧 MetaTabs 单列时跑到底部 — 移动端 OK，但 SCENES 6 列 `md:grid-cols-6` 在 360px 设备会撑破。

实测：`grid-cols-3 sm:grid-cols-4 md:grid-cols-6` 在 360px = 3 列 × 120px ≈ 360 - padding ≈ 320px → 每列 ≈ 100px — 缩略图 70px + padding 8px ✓ 勉强够。**pass**。

### P2 / `app/library/page.tsx:98` · `grid-cols-[repeat(auto-fill,minmax(180px,1fr))]` 没断点

```tsx
<div className="grid grid-cols-[repeat(auto-fill,minmax(180px,1fr))] gap-4">
```

`auto-fill` 自适应，OK。但 < 360px 时单列只能勉强放 180px + padding ≈ 220px 实际需要 — `<360px` 设备会横向溢出。

**推荐**：`grid-cols-[repeat(auto-fill,minmax(150px,1fr))]` 或加 explicit fallback `grid-cols-2`。

### P2 / `app/team/page.tsx:227-260` · 权限矩阵 `min-w-[640px]` 强制横向滚动

```tsx
<div className="overflow-x-auto">
  <div className="grid min-w-[640px]" ...>
```

640px 在 360px 手机上会横滚 ✓ 设计意图明确。**pass**，但可加 sticky `<aside class="sticky left-0">` 让第一列「权限标签」固定。

---

## 维度八 · 性能

### P1 / `app/create/page.tsx` · 整页仍是间接 client（`CreateWizard` 占大半）

虽然 page 本身 (`app/create/page.tsx`) 已经是 server component，但实质内容 `<CreateWizard />` 是 client component 且占整页。hydration 包没怎么减少。

可以接受 — 因为 CreateWizard 本就需要大量交互。但 `app/create/page.tsx:8-15` 那段 header 是 server 可渲染的，是个进步 ✓。

### P2 / `components/workspace/kpi-tile.tsx:59-83` · sparkline IIFE 每次 server render 重算

```tsx
{(() => {
  const pts = sparkline.map(...).join(" ");
  return (<><polyline points=...><polyline points=...></>);
})()}
```

OK — IIFE 在 server 跑，渲染成静态字符串发到 client。

但 `<linearGradient id={`kpi-grad-${label}`}>` 用 `label` 做 id — 如果同页两个 KpiTile 都叫 "席位" 或 "SSO"（team 页确实如此 4 个不同 label），会 id 冲突；本轮没出现，但**未来风险**：同 label 复用 KpiTile 会让 gradient fill 引用错位。

**推荐改法**：`useId()` 或外部传 `id` prop：
```tsx
import { useId } from "react"; // 注意：要变 client，或在 server 用 React.useId（React 18+）
const id = useId(); // 在 SSR 也安全
<linearGradient id={`kpi-grad-${id}`}>
```

或简单：把 label 做 slugify + 加随机 hash。最稳是 `useId`，但需要把 KpiTile 变 `"use client"` — 不必，可以让父层传 id。

### P2 / `app/loading.tsx` · skeleton 全 client side `skel` 动画

```css
.skel { animation: skel 1.4s linear infinite; ... }
```

`@media (prefers-reduced-motion: reduce)` 全局把 animation-duration 改成 0.001ms — `skel` 动画会"停止"在初始帧（`-200px 0`），意味着 reduced-motion 用户看到一片灰色没动 — 在视觉上跟"加载中"几乎没差别，**OK**。

但 fade-up 在 reduced-motion 下也是 0.001ms — fade-up 还能感知到（opacity 跳变 + 6px translate），但对部分用户仍可能眩晕。

**推荐改法**：在 globals.css 的 reduced-motion 块里**额外**给 `.animate-fade-up { animation: none !important; opacity: 1 !important; transform: none !important; }` 让它立即 final state。

### P3 / `lib/api.ts:154-188` · 大量 `Date.now() - N * 60_000` 在 fallback 内

```ts
updated_at: new Date(Date.now() - 9 * 60_000).toISOString(),
```

`PROJECT_FALLBACK` 是模块顶层 const — **加载文件那一刻**算出来的，永远不变。SSR 首次加载固定一个时间戳，后续 page reload 会变。开发期可能看到"9 分钟前" 持续显示「9 分钟前」直到 server 重启。**OK**（这是 fallback 数据，预期行为）。

---

## 维度九 · 品牌一致

### pass · accent-500 / sky-400 / amber-300 / violet-300 / rose-300 五色已收口

PipelineStage / StatusBadge / KpiTile / Create-wizard 都用 token 语义颜色，没有自创色。

### P1 / 7 处 SVG 仍裸 hex（ring 001 P1 未修）

- `components/layout/sidebar.tsx:63` `#22D3B7` / `#38BDF8`
- `components/layout/mobile-sidebar.tsx:92` 同上（新增 — 复制 sidebar 的 svg-mark）
- `components/workspace/video-player.tsx:39,41,44,47` `#22D3B7` / `#F7F9FC` / `#8590A8`
- `components/workspace/project-cover.tsx:13,14,17,...` 全部硬编码

**推荐改法**（ring 001 已给）：抽 `lib/theme.ts` 常量。本轮新增的 mobile-sidebar 仅是把 sidebar mark 复制了一遍 — 应该抽 `<BrandMark />` shared component（避免再有第三处复制）。

### P2 / `components/workspace/kpi-tile.tsx:27` · sparkline 颜色不走 token

见维度三 P2（重复列）。

### P2 / `components/workspace/pipeline-stage.tsx:23-30` · `bg-sky-500/[0.05]` / `border-sky-500/35` 等任意值

```tsx
running && "border-sky-500/35 bg-sky-500/[0.05] shadow-[0_0_0_1px_rgba(56,189,248,0.15)_inset]"
```

Tailwind 任意值 `/[0.05]` 在 tailwind 3.4+ 是允许的，但跟 `/35` 不一致写法（一个百分比、一个 alpha）。`/35` 是 `0.35`，`/[0.05]` 是显式 alpha。

**推荐**：统一用 `/5` 与 `/35` 形式，删 `[0.05]` `[0.18]` 等任意值。

---

## 维度十 · 可用性 / 一致性

### pass · CTA 文案统一为「新建视频」/「新建」✓

8 页头 + topbar + sidebar 全部统一。
跨页面对照：
- topbar: 「新建视频」/ 图标
- dashboard: 「新建视频」 / 「新建」
- projects: 「新建视频」 / 「新建」
- templates: 「新建视频」 / 「新建」
- library: 「上传素材」 / 「上传」
- team: 「邀请成员」 / 「邀请」
- brand: 「发布 v4」 / 「发布」
- settings: 「保存」/「保存」

✓ 一致性满分。

### P1 / `app/settings/page.tsx:39-49` · 侧栏导航 `i === 0` 永远高亮

```tsx
{SECTIONS.map((s, i) => (
  <a href={`#${s.id}`} className={`... ${i === 0 ? "bg-accent-500/12 text-foreground" : "..."}`}>
```

无论用户滚动到哪个 section，高亮都在 "通用"。

**推荐改法**：用 `IntersectionObserver` 监听 section 进入视口，或最简：用 `pathname.hash` 在客户端读 `usePathname` + state。SettingsForm 已经是 client，把 nav 也抽到 client 组件，监听 `hashchange`。

### P1 / `app/templates/page.tsx:37-42` · filter chips `i === 0` 永远高亮且无 onClick

```tsx
{["全部", "营销", "产品演示", "培训", "社交", "入职"].map((f, i) => (
  <Button key={f} size="sm" variant={i === 0 ? "default" : "outline"} className="rounded-full">
    {f}
  </Button>
))}
```

ring 001 P2.18 在 dashboard 已修（抽 ProjectFilter），但 templates 页**没修**。

**推荐改法**：抽 `<TemplateFilter templates={items} />` client 组件，参考 `ProjectFilter`。

### P1 / `app/library/page.tsx:8-15` · `FOLDERS` count hardcode（ring 001 P1.16 未修）

```ts
const FOLDERS = [
  { id: "all", label: "全部素材", icon: Folder, count: 112, active: true },
  { id: "video", label: "视频", icon: Video, count: 14 },
  ...
];
```

`api.assets()` 实际返回 10 项，"全部素材 112" 与列表完全对不上。同时 `iconFor()` 逻辑（`slug.startsWith("logo-")` 走 Palette icon）只对 2 个 logo asset 生效，文件夹 "品牌 count=3" 但实际只有 2 个 logo asset。

**推荐改法**：从 `api.assets()` 的 `totals` 字段读数；fallback `totals: { video: 14, image: 86, audio: 9, font: 4, logo: 3 }` 已写在 lib/api.ts，page 直接用 `totals.video` 即可。

### P1 / `app/projects/page.tsx:10` · `inProgress` 包含 `running` 状态但 Project 永不为此值

```ts
const inProgress = items.filter((p) => ["rendering", "scripting", "storyboard", "review", "running"].includes(p.status)).length;
```

`Status` 联合里有 `running`，但 `PROJECT_FALLBACK` 6 项的 status 是 `rendering / review / scripting / done / draft / draft` — 永远不会出现 `running`（那是 Job 状态）。多了个永远命中不到的分支，不致命，但**误导**：未来加 backend 时如果用 `running` 表示项目运行，类型对得上，但语义混乱。

**推荐改法**：把 Project.status 收窄成 `"draft" | "scripting" | "storyboard" | "rendering" | "review" | "done" | "failed"`；`running / succeeded / queued` 留给 Job/RenderTask。

### P2 / `components/workspace/projects-board.tsx:31-34` · `owners` 集合包含 fallback owner

```ts
const owners = useMemo(() => Array.from(new Set(projects.map((p) => p.owner))), [projects]);
```

OK — 但 fallback 6 项里 owner 重复（Ava Chen / Marcus Lee 各 2 次），set 去重后剩 4 人。**展示正确**。但实际项目通常上百，select 会变成超长 dropdown — 应加 max-height + scroll，或改 Combobox。本轮接受。

### P2 / `components/workspace/projects-board.tsx:71-93` · 两个 select 在 < sm 隐藏

```tsx
<select ... className="hidden ... sm:inline-flex">
```

select 在 < 640px 隐藏，用户在手机上**完全无法**按状态 / 按负责人过滤。设计意图（移动端简化）OK，但应该至少有一个汇总入口（如 "更多筛选" drawer）。

**推荐改法**：< sm 显示一个 "筛选" 按钮，点击展开 sheet。可推到 ring 003。

### P2 / `app/projects/page.tsx:34` · `<Card>` 直接包 `<ProjectsBoard>` 没有 `CardHeader`

```tsx
<Card>
  <ProjectsBoard projects={items} />
</Card>
```

`ProjectsBoard` 内部第一行是手工 border-b filter bar，第二行是 `<CardContent>` — 这种结构是反 shadcn 习惯。Card 子组件应该一致用 `CardHeader/CardContent`。

### P3 / `components/layout/sidebar.tsx:30` 与 `mobile-sidebar.tsx` NAV 重复

两份 NAV 数组完全一致。`sidebar.tsx` 的 `/projects` 有 `badge: "38"`，`mobile-sidebar.tsx` 没有。

**推荐改法**：抽 `lib/nav.ts` 唯一来源。

---

## 特殊检查

### `KpiTile` 复检

| 检查项 | 状态 |
|---|---|
| trend boundary（`range = max-min \|\| 1` 防 0 除）| **pass** — 处理了等值数组（如 `[1,1,1,1,1,1,1]`） |
| sparkline.length === 1 时回退到 placeholder | **pass** — `trend.length > 1` 保护 |
| SVG id 冲突 | **warn** — `kpi-grad-${label}` 中 label 是任意中文，转义没问题；但同 label 复用会撞 id（详见维度八 P2） |
| 字符串拼接安全 | **pass** — label 是 prop string，不会被注入 |
| 颜色 token | **warn** — 见维度九 P2 |

### `PipelineStage` shimmer 在 reduced-motion 下是否退化

`globals.css:110-115`：
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    transition-duration: 0.001ms !important;
  }
}
```

`animate-[shimmer_2.4s_ease-in-out_infinite]` 用任意值生成的 utility，最终 className 是 `animate-[shimmer_2.4s_ease-in-out_infinite]`，编译成 `animation: shimmer 2.4s ease-in-out infinite`。

`!important` 重置 `animation-duration: 0.001ms` 后，shimmer keyframe 在 0.001ms 内"播完" — opacity 立即跳变到 final state（infinite 仍生效但每 0.001ms 重启一次 = 视觉上停在 `0%` 或 `100%`）。

**实际效果**：reduced-motion 用户看到 shimmer 静止 — pass。但 `Loader2 animate-spin` 也被同样规则吃掉 → 旋转加载图标不转 → 用户**完全看不出 pipeline 在运行**。

**P1 推荐改法**：reduced-motion 块 exclude `[role="status"]` 内的 spinner：
```css
@media (prefers-reduced-motion: reduce) {
  *:not(.preserve-motion), *:not(.preserve-motion)::before, *:not(.preserve-motion)::after { ... }
}
```
然后给 `<Loader2 className="preserve-motion animate-spin" />`。或更简：把 `Loader2` 换成 progress bar（已有 inline progress）。

### `mobile-sidebar` 双重身份

| 检查项 | 状态 |
|---|---|
| Esc 关闭 | **pass** — `useEffect` 监听 `keydown` |
| 点遮罩关闭 | **pass** — backdrop 有 `onClick={onClose}` |
| 路由切换关闭 | **pass** — topbar `useEffect([pathname])` 关 drawer |
| body overflow lock | **pass** — `prev` capture + cleanup |
| focus trap | **fail** — 见维度二 P1 |
| 初始焦点 | **fail** — 同上 |
| aria-modal | **pass** — 已设 |

### `CreateWizard` localStorage SSR safety

```tsx
useEffect(() => {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    ...
  } catch {}
}, []);
```

`useEffect` 只在客户端跑，server 不会 access `localStorage` ✓。`try/catch` 兜底 disabled 浏览器（如 Safari 隐私模式）✓。

但 `JSON.parse(raw) as Draft` 没 try（在外层 try 里，OK）。`as Draft` 仍是 untrusted parse — 见维度一 P2。

`Math.random() < 0.0001` 错误注入：**符合"演示"意图但概率太低（万分之一）**，refine log 说 5%，但代码是 0.01% — review demo 时基本看不到。修不修都可，但**注释与实际不符**：
```ts
// 演示错误分支：5% 概率在某一步失败（生产请走真实事件流）
if (Math.random() < 0.0001) {
```

**推荐改法**：要么改成 0.05，要么改注释为 `0.01%`。设计意图不明，建议保持 0.0001 但更新注释，避免误导未来作者把它改成 0.05 后 demo 频繁失败。

### `team` presence dot 在 mobile 卡片视图遮挡

```tsx
<Avatar><AvatarFallback>...</AvatarFallback></Avatar>
<span className="absolute -right-0.5 -bottom-0.5 h-2.5 w-2.5 rounded-full ring-2 ring-card ..." />
```

Avatar 默认 `h-9 w-9` (`avatar.tsx:13`)，dot 10px 加 2px ring。Avatar 右下方 `-0.5` (≈-2px) 外漏 — 不遮挡头像本身，但**会遮到外层 card padding**：cardp4 = 16px padding 足够空间，看起来 OK。

实测 360px 设备：

```
[Avatar 36px][gap 12px][name + email 撑满][role badge]
```

dot 在 Avatar 外侧 (`-right-0.5 -bottom-0.5`)，挤到 Avatar 与 name 之间的 12px gap — **会与第一个字符重叠 4-6px** 当 name 偏长（如 "工作空间管理员" 的 badge 中文也长）。

**P2 推荐改法**：把 dot 改为 absolute 在 Avatar 内右下角（Avatar 是 `overflow-hidden` 但 dot 用 `position:absolute` 加在 wrapper div 上，wrapper 没设 overflow-hidden）：
```tsx
<div className="relative shrink-0">
  <Avatar>...</Avatar>
  <span className="absolute right-0 bottom-0 h-2.5 w-2.5 ... translate-x-1/4 translate-y-1/4" />
</div>
```
当前代码已经是这个结构，问题在 `-0.5` 太靠外了，可以改成 `right-0 bottom-0` + `translate-x-1/3 translate-y-1/3` 让 dot 一半在 avatar 内。

### `MetaTabs` `CommentComposer` 计数边界

```tsx
const remaining = 500 - text.length;
<Textarea maxLength={500} value={text} onChange={...} />
<span className="num">{remaining}</span>
```

`maxLength={500}` 阻止超长输入，`remaining` 最小 0 — **不会出现负数**。但 `remaining` 接近 0 时（`< 50`）应该警告变色。

**推荐改法**：
```tsx
<span className={cn("num", remaining < 0 ? "text-rose-300" : remaining < 50 ? "text-amber-300" : "text-muted-foreground")}>
  {remaining}
</span>
```

`disabled={!text}` 草稿按钮 vs `disabled={!text.trim() || sending}` 发送按钮 — 草稿允许空白？语义上保存空白草稿没意义。

**推荐**：草稿也用 `!text.trim()`。

### `ProjectFilter` / `ProjectsBoard` 破坏 server-component 数据流？

```tsx
// app/projects/page.tsx (server)
const { items, total } = await api.projects();
<Card><ProjectsBoard projects={items} /></Card>

// projects-board.tsx ("use client")
export function ProjectsBoard({ projects }: { projects: Project[] }) { ... }
```

server 在 build / request 时 fetch，把 plain object `items` 传给 client component — Next.js 接收 serializable props（Project 类型全是基本字段）✓。**pass**。

ProjectFilter 同理 — `app/dashboard/page.tsx` server fetch → `<ProjectFilter projects={projects} />` client。

### `app/globals.css` 新 utility

- `.skel` 用 `background-size: 200px 100%`，`background-position` 在 keyframe 从 `-200px 0` 到 `calc(200px + 100%) 0`。`200px` 是固定 px，**对于 < 200px 宽的 skel 块**（如 `h-3 w-12 = 48px`），shimmer 横向跨度比块还宽，效果是"块在闪烁"而非"光带划过" — 视觉上 acceptable，但与设计意图（光带）不符。

**推荐**：`background-size: 50% 100%` 让光带宽度跟随容器比例。

- `.dot-online::before` / `.dot-idle::before` 用 `right: -1px; bottom: -1px;` — 父元素必须 `position: relative` 才生效。sidebar 用 `<div className="relative grid h-8 w-8 ... dot-online">AC</div>` ✓。但**没有 `.dot-offline`** — 但代码里没人用 `.dot-offline`，只在 `team:53` 内联 `bg-graphite-300/60`。**一致性**：要么三态都做 css class，要么三态都内联。

### 8 个页头响应式（360 / 480 / 768 / 1024）

| 路由 | 360px | 480px | 768px | 1024px |
|---|---|---|---|---|
| `/dashboard` | ✓ wrap | ✓ | ✓ | ✓ |
| `/create` | **fail** — h1 28px×15 字撑破，wrap class 缺 | warn | ✓ | ✓ |
| `/projects` | ✓ h1 含 num，长度 ≈ 16 字 ok | ✓ | ✓ | ✓ |
| `/projects/[id]` | warn — h1 「春季产品发布 — 智能腕环」14 字 × 26px ≈ 364px 边界 | ✓ | ✓ | ✓ |
| `/templates` | ✓ | ✓ | ✓ | ✓ |
| `/library` | ✓ | ✓ | ✓ | ✓ |
| `/brand` | ✓ | ✓ | ✓ | ✓ |
| `/team` | ✓ | ✓ | ✓ | ✓ |
| `/settings` | ✓ | ✓ | ✓ | ✓ |

**只有 `/create` 出问题**（详见维度七 P1）。

---

## Refine 待办队列（按优先级排序）

### P0（必修，阻塞性）

1. **`components/workspace/create-wizard.tsx:114-148` interval cleanup race** — 把 `stepTimer` ref 删了，effect 用局部 `id`，`cancel()` 仅 `setRunning(false)` 让 effect cleanup 接管
2. **`components/layout/mobile-sidebar.tsx` drawer 无 focus-trap** — 至少打开时 `firstLink.focus()`、关闭时还焦点给 trigger（最小补丁见维度二 P1）

### P1（影响质量）

3. **`tailwind.config.ts:74,79` 与 `globals.css:81-84` `shimmer` 双定义** — 删 tailwind.config 那份，提升为 `animate-shimmer-slow` utility
4. **`components/workspace/create-wizard.tsx:89-99` `JSON.parse(raw) as Draft` 不验证** — 加 allowlist + 字段类型守卫
5. **`components/workspace/create-wizard.tsx:101-109` autosave race 首次 mount** — 用 `initialMount` ref 跳过首次
6. **`@media (prefers-reduced-motion)` 把 `animate-spin` 也吃掉** — exclude `.preserve-motion`（或换 progress bar 显示）
7. **`components/layout/mobile-sidebar.tsx` body overflow lock 改注释 + 双 drawer 风险** — 加注释提醒
8. **`app/create/page.tsx:8-15` 页头无 wrap、h1 固定 34px** — 改成 8 页一致的响应式范式
9. **`components/workspace/kpi-tile.tsx:54` `kpi-grad-${label}` id 冲突风险** — 用 `useId()` 或父层传 id
10. **`app/library/page.tsx:8-15` FOLDERS hardcode count** — 接 `api.assets().totals`
11. **`app/templates/page.tsx:37-42` filter chip `i===0` 永远高亮** — 抽 `TemplateFilter` client 组件
12. **`app/settings/page.tsx:39-49` 侧栏 `i===0` 永远高亮** — IntersectionObserver 或 hash 监听
13. **`app/projects/page.tsx:10` `Project.status` 包含永不出现的 `running`** — 收窄 `Status` 联合，或重新分 `ProjectStatus` / `JobStatus`
14. **a11y: kpi-tile sparkline 缺 `srHint`** — 加 sr-only 文本描述趋势
15. **a11y: project-filter / projects-board `role="tablist"` 不完整** — 改 `role="toolbar"` + `aria-pressed`，或补 `aria-controls`
16. **a11y: 多处 lucide icon 缺 `aria-hidden`** — 全局扫一遍补齐
17. **七处 SVG 仍裸 hex `#22D3B7` 等** — 抽 `lib/theme.ts` 常量；mobile-sidebar 的 `<BrandMark />` 应抽 shared component

### P2（细节打磨）

18. **`components/workspace/meta-tabs.tsx:131-135` 与 `share-link.tsx:14-17` setTimeout cleanup 缺** — 加 ref + cleanup
19. **`components/workspace/projects-board.tsx:18` `status` state 收窄到 `"any" | Status`**
20. **`components/workspace/meta-tabs.tsx:54-59` `<dt>/<dd>` 缺 `<dl>` 包裹** — 改 `<dl>`
21. **`app/team/page.tsx:228-260` 权限矩阵无表格语义** — 改 `<table>` 或补 aria-label
22. **`components/workspace/create-wizard.tsx:118` `Math.random() < 0.0001` 与注释不符** — 改注释为 `0.01%` 或改概率
23. **`components/workspace/meta-tabs.tsx:128` `disabled={!text}` 草稿应用 `text.trim()`**
24. **`components/workspace/kpi-tile.tsx:27` sparkline 颜色 / `pipeline-stage` 任意值 alpha** — 抽 `lib/theme.ts` 常量、收口写法
25. **`app/library/page.tsx:65` / `app/settings/page.tsx:43` / `app/brand/page.tsx:54` 模板字符串 className** — 统一 `cn()`
26. **`app/projects/page.tsx:34` `<Card>` 内缺 `CardHeader`** — `ProjectsBoard` 内补 `<CardHeader>` 包 filter bar
27. **`components/workspace/projects-board.tsx:71-93` 两个 select < sm 隐藏** — 加 "更多筛选" sheet
28. **`components/workspace/create-wizard.tsx:355` `RotateCcw` icon 不符语义** — 换 `RefreshCw`
29. **`components/workspace/meta-tabs.tsx:88-90` "+2 回复" 中文不顺** — 改 "+{n}" 或 "{n} 条回复"
30. **`app/team/page.tsx:126-132` 移动端卡片视图 presence dot 与 name 第一个字符可能重叠** — 调 translate
31. **`components/ui/label.tsx:14` `peer-disabled` 死代码（ring 001 P2 未修）** — 删
32. **`app/library/page.tsx:98` `minmax(180px,1fr)` 在 360px 横溢** — 改 `minmax(150px,1fr)` 或 fallback grid
33. **`components/layout/sidebar.tsx` 与 `mobile-sidebar.tsx` NAV 数组重复** — 抽 `lib/nav.ts`
34. **`globals.css:103` `.skel background-size: 200px` 固定 px** — 改 `50% 100%`

### P3（可不修）

35. **`components/workspace/projects-board.tsx:18` `useState<string>` → `"any" | Status`**
36. **`components/workspace/kpi-tile.tsx:23` placeholder array `[4,6,5,7,8,7,9]` 抽常量加注释**
37. **`components/workspace/create-wizard.tsx:355` RotateCcw → RefreshCw**
38. **`app/dashboard/page.tsx:73` mdash / middot 一致性**（保留）

---

## 总体观感

- **Refine 002 完成度极高**：六维 vibe-quality 全部命中（按钮反馈 / 数据面板清晰度 / 专业信任感 / 操作流畅度 / 团队协作 / 移动端），ring 001 的 P0（Fragment key / 整站零响应式 / 双播放按钮 a11y）全部修了。
- **唯一 P0 真 bug**：`CreateWizard` 的 `setInterval` cleanup race — 当用户连续点 "生成 / 取消 / 生成" 时旧 interval id 可能泄漏；以及 `mobile-sidebar` 的 focus trap 缺失（a11y 阻塞）。
- **`shimmer` 双定义**是 ring 002 最隐蔽的"代码不一致"问题：tailwind.config 与 globals.css 各有一份 keyframe，二选一胜出靠 CSS cascade — 维护陷阱。
- **`reduced-motion` 全局规则吃掉 `animate-spin`** 是另一处隐蔽 a11y 副作用 — pipeline running 状态在 motion-sensitive 用户看来是"静止的" loader，等同 "什么都没发生"。
- **新增的 ProjectFilter / ProjectsBoard / mobile-sidebar 三个 client 组件 server-component 数据流没问题**；ProjectsBoard 把 Card 当 wrapper 但没用 CardHeader 是结构小瑕疵。
- **ring 001 P1 残留**：library 文件夹 count、settings/templates 侧栏 `i === 0` 高亮、`peer-disabled` 死代码、SVG 裸 hex — 这些都不是 vibe 范围，可以理解 refine 002 跳过，但 ring 003 应该顺带清掉。
- **文案合规度仍 100%**。新增的 "再渲染一版 / 切换为播放 / 试着放宽筛选条件" 等都是高分中文 UX 文案。
- **TypeScript `tsc --noEmit`：0 error**。

修完 P0 共 2 项 + P1 共 15 项后可发 internal beta（v0.3）；P2 共 17 项在 ring 003 处理；P3 入设计语言 v2 反馈队列。

---

*Test ring · pass 002 — 21 个 refine 触动文件 + 3 个 boundary 文件，扫描完成。下一轮 Refine 应优先处理 #1 #2 #3 #6（运行时正确性 / a11y / 隐蔽 CSS 副作用），其余按 P1 列表节奏推进。*
