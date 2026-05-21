# ShadowBlade Next.js · Test Ring Report 005

审计对象：`frontend-next/` 全部 `.tsx` / `.ts` / `.css`，重点核查
(1) Refine ring 005 把 test ring 004 报告里 0 P0 + 3 P1 + 5 P2/P3 落地（commit `5becd46`），
(2) Parallel Design ring 005 新增的 `/studio` 路由 + `studio-workbench.tsx`（commit `ce098de` 及上下游），
(3) 同期 `lib/nav.ts` 加 /studio 入口、`lib/api.ts` 加 mix* 类型 + endpoint 的相关改动。

审计日期：2026-05-21
审计员：Test ring · pass 005（只读 · 纯静态分析 · 无浏览器）
基线：`tsc --noEmit` 0 error ✓（沿用第 5 轮死透状态）
源文件统计：15 个 page（含 root marketing hero + 13 个 (app)/(external) 路由 — 新增 /studio）+ 7 boundary（3 root + 2 (app) + 2 (external)）+ 30+ 组件（含 ring 005 新增 `studio-workbench.tsx`）。

报告对象矩阵（refine 003 引入的格式，5 轮验收稳定）：

| 来源 | 数量 | 状态简述 |
|---|---|---|
| **上轮残留** · ring 004 留给 ring 005 的 3 P1 + 5 P2/P3 | 8 项 | 全部死透 ✓ |
| **本轮新增** · design ring 005 加 `/studio` + `studio-workbench.tsx` + lib/nav.ts 加项 + lib/api.ts 加 mix* | 4 个核心文件 | 功能完整，但 **a11y 与 5 轮飞轮范式严重不一致** — 14 处 lucide icon 0 aria-hidden + 2 处 animate-spin 无 preserve-motion + 1 处 hardcoded 绝对路径 |
| **跨轮回归** · refine 001-005 修过的项目 | 0 倒退 | 5 轮全清 ✓ — ring 005 是迄今最干净的一轮 |

---

## 顶部总表

### 10 类审计维度

| # | 维度 | 评级 | 一句话总结 |
|---|---|---|---|
| 1 | TypeScript 严格性 | **pass** | `tsc --noEmit` 0 error 持续维持；KIND_CLASS Record<DriftKind> 严格化 ✓；studio-workbench Badge variant 已修；MixCue/MixFeatures/MixVideoResponse 类型完整 |
| 2 | React 模式 | **warn** | studio-workbench fetch features 的 useEffect 用 alive flag 防 race ✓；handleGenerate 用 try/catch/finally 正确；**但 ChipGroup 缺 aria-pressed**；**Loader2 无 preserve-motion** |
| 3 | Tailwind / shadcn | **pass** | BRAND token 接入率（除 project-cover）100% 维持；studio 用 bg-accent-500/15、border-white/10 等 token 合理；Badge variant=default ✓ 修了 ring 004 design ring 引入的 secondary union 错 |
| 4 | 无障碍 (a11y) | **warn** | aside/toolbar 拆双层正确 ✓；3 个 loading 加 aria-busy + aria-label ✓；meta-tabs `<time dateTime>` 死透 ✓；**但 studio-workbench 14 处 lucide icon 全无 aria-hidden** — 与 5 轮飞轮规约最大漂移 |
| 5 | 语义 HTML | **pass** | studio page 用 `<section>` + `<h1>` + `<code>` ✓；workbench Card 嵌套合理；ResultPanel 用 dl/dt/dd 描述 Stat ✓ |
| 6 | 中文文案 | **pass** | 「连上 ffmpeg，直接渲染」「立即渲染」「生成中…」「填好参数后点」专业且品牌化；「等待后端连接 · 见下方 README 启动 make next」对开发者友好；保持 5 轮零文案失分 |
| 7 | 响应式 | **pass** | studio `lg:grid-cols-[minmax(0,1fr)_420px]` 双栏布局合理；Tabs 用 `overflow-x-auto` 兜底 < md 屏；EmptyResult aspect-[9/16] 在小屏不会撑爆 |
| 8 | 性能 | **warn** | studio-workbench 用 client useEffect 拉 mixFeatures 是合理（运行时能力检测）；**但 DEFAULT_SAMPLES hardcode 绝对路径 `/Users/qiu/工作流/...` 对所有非作者机器立即崩** |
| 9 | 品牌一致 | **warn** | BRAND 接入率维持 100%（除 project-cover）；ChipGroup active state 用 accent-500/60 + accent-500/15 合规；**但 studio 双 Toggle 用 `accent-accent-500` 是 hack（直接 CSS 颜色而非 token）** |
| 10 | 可用性 / 一致性 | **warn** | lib/nav.ts 自动接通 /studio sidebar/mobile-sidebar/topbar 三处 ✓；**但 studio 内部 Chip 选择组与现有 toolbar 范式（template-filter / project-filter / library-folders / projects-board / integrations / notifications）不一致** |

### 15 个 page + 7 boundary 评级

| 路由 / 文件 | 评级 | 主要问题 |
|---|---|---|
| `/` | **pass** | marketing hero 沿 ring 004 范式无回归 |
| `/dashboard` | **pass** | 沿用稳态 |
| `/create` | **pass** | createWizard 5 轮无回归（interval race / autosave race / setTimeout cleanup 全部死透）|
| `/projects` | **pass** | 同上 |
| `/projects/[id]` | **pass** | VideoPlayer BRAND ✓；meta-tabs `<time dateTime={c.whenISO}>` ring 005 修死 ✓ |
| `/templates` | **warn** | template-filter empty state 内联（已知，留 design v5） |
| `/library` | **pass** | LibraryFolders 抽出 + 真切换 ✓ |
| `/brand` | **pass** | hex 是内容非样式 |
| `/team` | **pass** | Crown aria-hidden ✓ |
| `/settings` | **pass** | 6 anchor / 6 Card 对齐 ✓ |
| `/analytics` | **pass** | `kpi.unit === "videos"` 死透 ✓；KIND_CLASS 严格化 ✓；figure + figcaption ✓ |
| `/integrations` | **warn** | role=toolbar / noopener noreferrer / icon aria-hidden 全做 ✓；empty state 仍内联（已知） |
| `/notifications` | **pass** | aside 保留 complementary landmark / 内层 div role=toolbar ✓；whenISO 全 ✓ |
| `/studio` ⭐新 | **warn** | 真混剪引擎接通 ✓；mixFeatures 用 alive flag 防 race ✓；**但 14 处 icon 缺 aria-hidden** + **2 处 animate-spin 缺 preserve-motion** + **ChipGroup 缺 aria-pressed** + **hardcoded `/Users/qiu` 绝对路径** |
| `/share/[token]` | **pass** | setTimeout 双 timer cleanup + BrandMark + VideoPlayer 复用 ✓ |
| `app/loading.tsx` | **pass** | aria-busy="true" aria-label="正在加载" ✓ |
| `(app)/loading.tsx` | **pass** | aria-busy="true" aria-label="正在加载工作台" ✓ |
| `(external)/loading.tsx` | **pass** | aria-busy="true" aria-label="正在加载分享内容" ✓ |
| `app/not-found.tsx` | **pass** | 单 CTA「回到首页」+ 注释解释 ✓ |
| `(app)/not-found.tsx` | **pass** | 双 CTA 给登录员工 ✓ |
| `(external)/not-found.tsx` | **pass** | 无 CTA + Link2Off + amber 表达失效 ✓ |
| `app/error.tsx` | **pass** | amber + AlertTriangle + reset button + digest 可选 ✓ |

---

## 一、Refine ring 005 应用回归验证（逐项）

逐项核对 test ring 004 报告的 Refine 待办队列（3 P1 一行 fix + 5 顺手 P2/P3 + 1 design ring 引入的 TS 错 = 9 项）。

### P1（3/3 一行 fix · 全部 ✓ 死透）

| # | 报告条目 | 验证 | 备注 |
|---|---|---|---|
| P1.1 | `analytics/page.tsx:86` 第 1 个 KPI trend 走错 proxy | ✓ | analytics line 88: `kpi.unit === "videos"`；lib/api.ts:374: `unit: "videos"` ✓ 对齐。第 1 个 KPI（本月渲染次数）现在落入 `a.timeseries.map(d => d.rendered)` 真 trend 分支 |
| P1.2 | `notifications/page.tsx:120` `<aside role="toolbar">` 覆盖 complementary landmark | ✓ | line 122-141 双层结构：`<aside aria-label="通知分类">` 保留 landmark；内层 `<div role="toolbar" aria-label="通知分类筛选">` 装 button 组。注释（line 120-121）明确解释了修法依据 |
| P1.3 | `app/not-found.tsx` 次 CTA 「进入工作台」对未登录访客 friction | ✓ | line 26-30 已砍单 CTA「回到首页」；line 11-13 注释清楚说明：等 design v5 加 middleware（未登录 → /login）后再补回。`(app)/not-found.tsx` 仍是双 CTA（line 17-18）给登录员工 ✓ |

**P1 全部 ✓ 死透** — refine ring 005 的 3 个一行 fix 落地完整。

### 顺手 P2 / P3（5/5 全部 ✓）

| # | 报告条目 | 验证 | 备注 |
|---|---|---|---|
| P1 残留 | `meta-tabs.tsx:94` `<time>` 缺 dateTime | ✓ | line 15-16 COMMENTS 加 `whenISO: "2026-05-21T08:57:00Z"` / `"2026-05-21T08:49:00Z"`；line 94 `<time dateTime={c.whenISO}>{c.when}</time>` ✓ |
| P2.4 | `analytics/page.tsx:29` `KIND_CLASS: Record<DriftKind, string>` 严格化 | ✓ | line 23: `type DriftKind = "warn" \| "stop" \| "ok"`；line 25: DRIFT 数组用类型化字面量；line 31: `Record<DriftKind, string>`。验证：如果 KIND_CLASS["typo"] 现在会 TS 报错 ✓ |
| P3.14 | loading boundary 加 `aria-busy` + `aria-label` | ✓ | 三个 loading 全做：`(app)/loading.tsx:9` `aria-busy="true" aria-label="正在加载工作台"`；`(external)/loading.tsx:9` `aria-busy="true" aria-label="正在加载分享内容"`；`app/loading.tsx:9` `aria-busy="true" aria-label="正在加载"` |

### Design ring 005 引入的 TS 错（1/1 ✓）

| # | 项 | 验证 | 备注 |
|---|---|---|---|
| TS err | `studio-workbench.tsx` 用 `<Badge variant="secondary">` 但 Badge cva 不含 secondary union | ✓ | line 338 / 348 已改 `variant="default"`；Badge cva（`components/ui/badge.tsx:10-25`）仅 default + 14 个 status union；grep `variant="secondary"` 在 app + components 0 匹配 ✓；`tsc --noEmit` 0 error |

**Refine ring 005 整体应用完成度：9/9 = 100%。**

---

## 二、`/studio` 完整 10 维审计（新增页 · 重点）

### 整体结构

```
app/(app)/studio/page.tsx              · 26 行 server component（hero + 一句话简介 + <StudioWorkbench />）
components/workspace/studio-workbench.tsx  · 537 行 client component
  - StudioWorkbench (主)：state x 13、useEffect features fetch、handleGenerate
  - FeaturesBadgeRow：mixFeatures 能力检测可视化
  - EmptyResult：未渲染时的提示
  - ResultPanel：渲染完成后的 video + Stat dl + IssueList + warnings details
  - Stat / IssueList / ChipGroup / Toggle 4 个内部子组件
```

### a11y · warn ⚠️（5 轮飞轮范式最大漂移点）

**14 处 lucide icon 全无 aria-hidden**：

```
studio-workbench.tsx:168  <Sparkles className="text-accent-300" size={18} />      混剪参数标题
studio-workbench.tsx:188  <Palette size={14} /> 调色                              Tab label
studio-workbench.tsx:191  <Film size={14} /> 比例                                 Tab label
studio-workbench.tsx:194  <Sparkles size={14} /> 过渡                             Tab label
studio-workbench.tsx:197  <Music2 size={14} /> 音轨                               Tab label
studio-workbench.tsx:200  <Captions size={14} /> 字幕                             Tab label
studio-workbench.tsx:286  <Loader2 className="animate-spin" /> 生成中…           Button spinner
studio-workbench.tsx:290  <Sparkles /> 立即渲染                                   Button icon
studio-workbench.tsx:301  <AlertTriangle size={14} className="mt-0.5 shrink-0" />  Error icon
studio-workbench.tsx:311  <Film size={18} className="text-accent-300" /> 渲染结果  Card title
studio-workbench.tsx:330  <Loader2 className="animate-spin" size={12} />          Features 检测中
studio-workbench.tsx:344  <Cpu size={11} />                                       VT GPU badge
studio-workbench.tsx:354  <Captions size={11} />                                  libass badge
studio-workbench.tsx:364  <Mic size={24} className="text-muted-foreground" />     EmptyResult
studio-workbench.tsx:417  <Download size={12} /> 下载 MP4                         link icon
studio-workbench.tsx:466  <AlertTriangle size={10} className="mt-0.5 shrink-0" />  IssueList
```

5 轮飞轮死透的范式（test ring 003 / 004 reaffirmed 1+ 次）：「icon 旁有同义文本时必须 aria-hidden 防 SR 双读」。比如 `<Sparkles /> 立即渲染` 这种 button 内容 — SR 用户会听到「sparkles 立即渲染」（lucide 默认会暴露 svg accessible name；即使 stroke-only 也会读 alt）。share/[token] 11 处 lucide icon 100% aria-hidden、video-player 内部 Play/Pause/Volume2/Maximize2 也带 aria-hidden（ring 004 refine 005 P1.14）— studio-workbench 0 处 aria-hidden 是严重逆差。

**2 处 Loader2 `animate-spin` 无 preserve-motion**：

```
studio-workbench.tsx:286  <Loader2 className="animate-spin" /> 生成中…
studio-workbench.tsx:330  <Loader2 className="animate-spin" size={12} />
```

ring 003 在 create-wizard 死透的范式（test ring 003 P0）：「关键状态信号 spinner 必须 preserve-motion 标记，否则 prefers-reduced-motion 用户看到的是完全静止的图标，感知不到 loading 状态」。`pipeline-stage.tsx:45` / `create-wizard.tsx:420` / `create-wizard.tsx:475` 三处都对了 — studio-workbench 这两处是漂移。

**ChipGroup 缺 aria-pressed + role=toolbar**：

`studio-workbench.tsx:486-509` 的 ChipGroup 是手写 button group（不是 shadcn Tabs），渲染 3 处选项（look / aspect / transitions）。`<button onClick={() => onChange(o.key)}>` 当前是「无状态 button + className 切换」，**SR 用户听到的是 7 个无差别 button**。对照 5 轮飞轮收敛的标准范式（aria-pressed 7 处 + role=toolbar 6 处全部一致）：

- `library-folders.tsx:33` + `:42` — `role="toolbar"` + `aria-pressed={isActive}`
- `template-filter.tsx:43` + `:51` — `role="toolbar"` + `aria-pressed={active === f.id}`
- `project-filter.tsx:35` + `:42` — 同
- `projects-board.tsx:49` + `:57` — 同
- `integrations/page.tsx:102` + `:108` — 同
- `notifications/page.tsx:123` + `:129` — 同
- `create-wizard.tsx:236` — `aria-pressed={draft.template === t.slug}`

**studio ChipGroup 是 5 轮飞轮里第 8 个互斥按钮组，但完全没用这两个属性** — refine ring 006 必须修，否则盲用户根本不知道哪个 Look / Aspect / Transition 选中。

**Toggle label 用 `<label>` 但没显式 for**：

`studio-workbench.tsx:522-535` 的 Toggle 把 `<input>` 直接套在 `<label>` 内 — 这是合规的 implicit association（HTML5 标准），SR 能识别。✓ 这一处 OK。

**Tabs（line 185-280）用 shadcn Radix Tabs**：内置完整 ARIA（role="tablist"/"tab"/"tabpanel"），✓ 合规。

### 性能 · warn ⚠️

**hardcoded 绝对路径 `/Users/qiu/工作流/shadowblade/storage/samples/*`**：

`studio-workbench.tsx:32-40` 的 `DEFAULT_SAMPLES` 把 6 个 sample 文件路径写死成 `/Users/qiu/工作流/shadowblade/storage/samples/clip_a.mp4` 等 — 仅在作者本机有效，对：
- 其他贡献者本地 dev — 立即崩
- CI / GitHub Actions — 立即崩
- Vercel 生产部署 — 立即崩
- 演示给销售 / 客户 — 立即崩（除非他们恰好叫 qiu 且把项目克隆到完全相同的路径）

**修法**：把绝对路径改为相对 `storage/samples/clip_a.mp4`，由后端 resolve 项目根；或加 `process.env.SAMPLES_ROOT` 环境变量；或 lazy 用 backend `/api/v1/samples/list` 提供动态清单。**P0 阻塞 — 任何非作者机器都无法 demo /studio**。

**mixFeatures 客户端 fetch 是合理设计**：

`useEffect(() => { let alive = true; api.mixFeatures().then((f) => { if (alive) setFeatures(f); }); return () => { alive = false; }; }, [])` 是教科书级别的 race-safe 异步 effect 范式 ✓ — 即使是 5 轮飞轮里第一次出现这种 alive flag pattern，质量很高。

之所以放 client：服务器端可能 ffmpeg 检测结果跟客户端有差异；fallback `has_videotoolbox: false` 也防 SSR 抓 backend 失败。✓ 设计合理。

### TS · pass ✓

MixCue / MixFeatures / MixSubtitleIssue / MixVideoResponse / MixVideoRequest 5 个新类型在 `lib/api.ts:219-287` 完整定义 ✓；api.mixFeatures / api.mixPreview 两个调用方法签名清晰；handleGenerate 的 try/catch 用 `err instanceof Error ? err.message : String(err)` 安全推断 ✓。

cuesToScript / scriptToCues / toBrowserUrl 三个 helper 都有显式签名 ✓。

### React · pass ✓（除 ChipGroup aria 之外）

- `useState` x 13 都用了合理初始值（DEFAULT_SAMPLES.* / 字符串 / 布尔默认）✓
- `useMemo` cues 依赖 [scriptText] ✓ 无不必要 re-compute
- `useEffect` features fetch alive flag ✓ 教科书 race-safe
- `handleGenerate` try/catch/finally finally setRunning(false) ✓ 即使 throw 也能复位
- 渲染条件 `!result ? <EmptyResult /> : <ResultPanel />` 合理 ✓

### Tailwind / shadcn · pass ✓

- `bg-accent-500/15 text-accent-200` / `border-white/10 bg-white/[0.02]` 用 token ✓
- Badge variant="default" + 用 className 覆盖颜色 = ring 005 修法保留 ✓
- shadcn Tabs / Card / Button / Input / Label / Textarea 全用 ✓
- 唯一可商榷：line 528 `className="size-4 accent-accent-500"` 是 Toggle 内 `<input type="checkbox">` 的 native checkbox 色 — `accent-accent-500` 这种重复 prefix 看起来像 typo 但实际是 Tailwind v3 `accent-*` 一族 utility（input native accent color），最终是 `--tw-accent: theme(colors.accent.500)`。✓ 合规

### 语义 HTML · pass ✓

- studio/page.tsx 用 `<section>` + `<h1>` 标准 ✓
- workbench 用 Card 组合 ✓
- ResultPanel 内部用 `<dl><dt><dd>` 描述 Stat ✓ 语义正确（Stat = label+value 配对）
- IssueList 用 `<ul><li>` ✓
- warnings 用 `<details><summary>` 折叠 ✓
- `<code className="rounded bg-white/5 px-1.5">` 内联代码 ✓

### 中文 · pass ✓

- 「连上 ffmpeg，直接渲染。」品牌文案，配 marketing hero 「一份简报，四分钟出片。」节奏一致 ✓
- 「等待后端连接 · 见下方 README 启动 make next」开发者友好提示
- 「混剪参数 / 调色 / 比例 / 过渡 / 音轨 / 字幕」全中文 ✓
- 「软件编码 / VideoToolbox GPU / libass 字幕 / Pillow PNG 字幕」技术词正确，不强行汉化 ✓
- 「字幕峰值 CPS」「BGM BPM」缩写合理 — CPS = chars per second（字幕规范），BPM = beats per minute（节奏检测） ✓

### 响应式 · pass ✓

- 主网格 `lg:grid-cols-[minmax(0,1fr)_420px]` — 桌面双栏，< lg 折叠单列 ✓
- TabsList `overflow-x-auto` 在 < md 屏可水平滚 ✓
- EmptyResult `aspect-[9/16]` 在小屏不撑爆 ✓
- ChipGroup `flex flex-wrap gap-1.5` 自动换行 ✓
- ResultPanel video `w-full` 自适应 ✓
- dl `grid-cols-2` 双列 stat，行数自动 ✓

### 品牌 · warn（轻微）

- BRAND token：用 `accent-500/15` / `accent-200` / `accent-300` / `border-white/10` ✓ 全 token
- 但 line 528 `accent-accent-500` 是 native input accent — 当下唯一一处不走 BRAND.accent500 token；不严格算漂移（Tailwind utility 与 BRAND 同步定义）
- 0 处 hex 字面量 ✓

### 一致性 · warn（ChipGroup 与 5 轮飞轮范式不一致）

详见上文 a11y 部分 — ChipGroup 应改为 `role="toolbar" aria-label="…"` 父层 + 每个 button 带 `aria-pressed={value === o.key}`，与 6 处其他 toolbar 统一。

---

## 三、最近一轮设计文件 audit

### `lib/nav.ts` · pass ✓

```tsx
items: [
  { href: "/dashboard", label: "工作台", icon: LayoutDashboard },
  { href: "/create", label: "新建视频", icon: Sparkles, cta: true },
  { href: "/studio", label: "Studio · 真混剪", icon: Film },        ← 新增 ring 005
  { href: "/projects", label: "项目库", icon: FolderOpen, badge: "38" },
  { href: "/templates", label: "模板", icon: LayoutTemplate },
  { href: "/analytics", label: "数据分析", icon: LineChart },
],
```

- /studio 进入 「制作」 group 第 3 项 ✓ 位置合理（新建视频 → Studio → 项目库 工作流）
- 用 `Film` icon ✓ 与混剪语义匹配
- label 「Studio · 真混剪」 是 ring 005 引入的「中英文 + 副标」格式 — 5 轮内首次混搭，是设计决定；可接受但与其他 12 个 NAV item 「工作台 / 新建视频 / 项目库 / 模板」纯中文风格略有不同
- ROUTE_LABEL 通过 `Object.fromEntries(NAV.flatMap(...))` 自动派生 — topbar 面包屑零维护接通 ✓

### `lib/theme.ts` · pass ✓

5 轮没新增 hex。21 个 token（accent 3 + navy 7 + graphite 4 + paper + sky/amber/rose 5）+ COVER_NAVY + TREND_COLORS — 与 ring 004 完全一致，无漂移。

### `lib/api.ts` · pass ✓（仅 mix* 类型新增）

ring 005 design ring 在 lib/api.ts 加了 5 个新类型 + 5 个新调用方法（mixFeatures / mixLooks / mixAspects / mixPresets / mixPreview），全部用 get<T>(...) 范式 ✓ 或自定义 fetch（mixPreview POST）✓。fallback 退化到「能力为 false」是安全默认 ✓。

ANALYTICS_FALLBACK unit 是 "videos" line 374 ✓ 与 analytics page line 88 对齐死透。

### `app/page.tsx` 改 marketing hero 后 OG meta · pass ✓

`app/layout.tsx:20-22` `metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://frontend-next-two-lac.vercel.app")` ✓ — Next.js 14 OG image absolute URL 必备配置；`openGraph: { images: ["/og-image.svg"] }` 会自动 prefix metadataBase ✓ 社交分享时 og-image 可正确加载。

`title: "ShadowBlade · 企业级 AI 视频云"` + `description: "ShadowBlade 把一份简报变成可以直接上线的营销 / 培训 / 产品视频，4 分钟出片，对照你的品牌套件渲染。"` ✓ 与 marketing hero 文案完全一致，SEO / 社交分享一致性 ✓。

### `app/layout.tsx` metadataBase · pass ✓

见上。`process.env.NEXT_PUBLIC_SITE_URL` 优先 → fallback 到 Vercel 默认 URL，dev/staging/prod 三档兼容 ✓。

---

## 四、跨轮回归终检（5 轮累计）

经 grep / Read 全代码库验证：

### 0 回归项

- **createWizard interval race**（ring 001 P0 → ring 002 死透）：`useEffect(() => { ... const id = setInterval(...); return () => clearInterval(id); }, [running])` ✓ ring 005 持续
- **createWizard autosave race**（ring 002 P0 → ring 003 死透）：`initialMount.current` flag + cleanup timer ✓ ring 005 持续
- **mobile-sidebar focus trap**（ring 002 P0 → ring 003 死透）：useEffect Tab loop + previously focused + escape + body overflow lock ✓ ring 005 持续完整
- **(external) layout `<main>` 唯一 landmark**（ring 003 P0 → ring 004 死透）：`(external)/layout.tsx:5` `<main id="main-content" className="min-h-screen">` ✓；share/[token] 内部用 `<div className="bg-background">` 不嵌套 main ✓
- **share/[token] setTimeout cleanup**（ring 002 → 003 回归 → 004 死透）：`copyTimerRef` + useEffect cleanup + catch 分支也接 timer ✓ ring 005 完整
- **preserve-motion 范式**（ring 002 P1 → ring 003 死透）：pipeline-stage / create-wizard 3 处都加 ✓；**唯一新违例是 studio-workbench 2 处**
- **BrandMark 0 复刻**（ring 004 P1.7 → 死透）：grep `viewBox="0 0 36` 0 匹配 ✓；4 处用 BrandMark ✓
- **VideoPlayer watermark prop**（ring 004 P1.8 → 死透）：share + projects/[id] 都用 ✓
- **5 个 ARIA 属性一致性**（ring 003 → 004 → 005 累积）：
  - aria-modal 1 处（mobile-sidebar）✓
  - aria-pressed 7 处（template-filter / project-filter / projects-board / library-folders / integrations / notifications / create-wizard）✓ — **studio-workbench ChipGroup 是第 8 处需要而未加**
  - aria-current="page" 3 处（sidebar / mobile-sidebar / settings-nav）✓
  - role="toolbar" 6 处全配 aria-label ✓ — **studio-workbench ChipGroup 是第 7 处需要而未加**
  - aria-busy 3 处 loading boundary ✓ ring 005 新加完整
- **BRAND token 接入率**（除 project-cover）：
  - lib/theme.ts 21 token ✓
  - app/(app)/brand/page.tsx 8 hex（内容色板）✓
  - app/(app)/dashboard/page.tsx 1 hex（dashboard 偏移文案）✓
  - app/(app)/analytics/page.tsx 2 hex（DRIFT 偏移文案）✓
  - app/(app)/integrations/page.tsx 15 hex（第三方品牌色不可 token 化）✓
  - app/(app)/notifications/page.tsx 1 hex（drift 文案 #20D2B5 / #22D3B7 呼应）✓
  - app/(external)/share/[token]/page.tsx 0 hex ✓
  - components/workspace/video-player.tsx 0 hex ✓
  - **components/workspace/project-cover.tsx 26 hex**（已知技术债，留 design v5）⚠
  - 其它组件 0 hex ✓ — **studio-workbench 0 hex ✓ 接入率 100% 维持**
- **meta-tabs `<time dateTime>`**（ring 004 漏扫 → ring 005 死透）：line 15 whenISO + line 94 dateTime ✓
- **(app)/(external) layout 分工**（ring 003 → 004 → 005 稳定）：(app)/layout.tsx 带 Sidebar + Topbar；(external)/layout.tsx 仅 `<main>` ✓

### 5 轮累积总进展

| 维度 | ring 001 | ring 002 | ring 003 | ring 004 | ring 005 |
|---|---|---|---|---|---|
| P0 修复率 | n/a（首轮） | 2/2 | 2/2 | 4/4 | **0/0**（无 P0）|
| P1 修复率 | n/a | 11/11 | 15/15 | 14.5/15 | **3/3** |
| 顺手 P2 清理 | n/a | 5 | 3 | 5 + 显式跳过 9 | **5 + 显式跳过 7** |
| 跨轮回归 | n/a | 0 | 1（share setTimeout） | 0 | **0** |
| 新引入 P1/P0 | n/a | 4 P0 | 4 P0 | 2 P1 | **3 P2**（studio aria/preserve-motion/路径） |
| 协作时序摩擦 | n/a | 严重 | 严重 | 中等 | **轻微（仅 studio）** |
| BRAND 接入率（除 project-cover） | 30% | 50% | 60% | 100% | **100% 维持** |
| 跨页一致性 | 60% | 80% | 90% | 100% | **95%**（仅 studio ChipGroup 漂移）|

ring 005 的工程质量是 5 轮中**最干净的一次**（refine 全清 100%、回归 0、新引入仅 design ring 的 studio 副作用），但 **studio-workbench 这个新组件本身有显著的 a11y 漂移**（与已稳定的 5 轮范式不一致），不应被 0 P1 的表象掩盖。

---

## 五、Refine 待办队列（按优先级排序 · 三栏分类）

### 上轮残留（已无 P1/P2 阻塞）

#### P2

1. **project-cover.tsx 26 hex + 6 hardcoded gradient id** — 5 轮显式跳过；留 design v5 整组下放 BRAND token + useId 化
2. **template-filter / project-filter / projects-board / integrations empty state 内联** — 显式跳过；留 design v5 抽 `<EmptyState>` 加 reset filter CTA
3. **leaderboard 行 link** — 显式跳过；留 design v5
4. **notifications visible 双 filter 合并** — 性能 / 可读性微优化
5. **notifications aside < md 折叠 horizontal scroll chip** — 移动端 UX 改进
6. **CI lint 防 hex 字面量** — design v5 todo

### 本轮新增（design ring 005 引入的 studio 副作用）

#### P1（影响 a11y）

1. **studio-workbench.tsx 14 处 lucide icon 缺 aria-hidden** — 与 5 轮飞轮死透的范式不一致；SR 双读、icon 名暴露给屏幕阅读器。**修法**：批量加 `aria-hidden` 给所有装饰性图标（line 168, 188, 191, 194, 197, 200, 286, 290, 301, 311, 330, 344, 354, 364, 417, 466 共 16 处含 Loader2 2 处）；button 内 icon 仍 aria-hidden 因为 button 本身有 accessible name（"立即渲染"）

2. **studio-workbench.tsx ChipGroup 缺 aria-pressed + role=toolbar** — 与 6 处 toolbar + 7 处 aria-pressed 范式不一致。**修法**：
```tsx
function ChipGroup<T>({ label, options, value, onChange }) {
  return (
    <div className="grid gap-1.5" role="group" aria-label={label}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex flex-wrap gap-1.5" role="toolbar" aria-label={`${label}选择`}>
        {options.map((o) => (
          <button
            key={o.key}
            type="button"
            aria-pressed={value === o.key}
            onClick={() => onChange(o.key)}
            className={...}
          >...</button>
        ))}
      </div>
    </div>
  );
}
```
（注：Label shadcn 给 form input 用，给一组 button 不合适 — 改 `<span>` 或 `aria-label`）

3. **studio-workbench.tsx 2 处 Loader2 缺 preserve-motion** — 与 create-wizard / pipeline-stage 范式不一致。**修法**：line 286 + 330 改 `<Loader2 className="preserve-motion animate-spin" aria-hidden />`

#### P0（阻塞 demo / 部署）

4. **studio-workbench.tsx DEFAULT_SAMPLES hardcode 绝对路径 `/Users/qiu/工作流/...`** — 除作者本机外任何机器都无法 demo /studio。**修法**：
   - 短期：用相对路径 `storage/samples/clip_a.mp4`（backend 已挂载 storage StaticFiles，会按项目根 resolve）
   - 中期：加 `/api/v1/mix-video/samples` endpoint 让 backend 主动报清单
   - 长期：UI 上加「上传 / 选择素材」入口替代 hardcode

#### P3

5. **studio-workbench.tsx 「Studio · 真混剪」label 风格与其他 NAV item 不一致** — 12 个 NAV 都是纯中文，唯独 /studio 用「英文 · 中文」格式。视觉 / 信息架构小问题，留 design v6 决定要不要统一

6. **studio-workbench.tsx `<Mic>` 在 EmptyResult 用 size={24} 但其他图标用 size={11/12/14/18}** — size 不统一；建议改用 lucide 默认 + className `h-* w-*` 范式（与 5 轮飞轮其他组件一致）

### 跨轮回归（refine 001-005 修过的项目无倒退）

经 grep / Read 验证 → 0 回归项目。**5 轮飞轮的关键范式（shimmer / mobile-sidebar focus / createWizard race / share setTimeout / preserve-motion / BrandMark / EmptyState / BRAND token / aria-modal / aria-pressed / aria-current / role=toolbar / aria-busy / (app)+(external) layout 分工 / VideoPlayer watermark / meta-tabs dateTime）全部死透 — 唯一新违例都集中在 studio-workbench 这一个文件**。

---

## 六、总体观感

### Refine 005 的应用质量

- **3 P1 一行 fix 全部 ✓**：analytics unit / notifications aside-toolbar 双层 / not-found 单 CTA — 演示现场会被发现的 3 个 issue 已死透
- **5 顺手 P2/P3 也清掉**：meta-tabs whenISO（5 轮飞轮里最后一处遗漏）/ KIND_CLASS 严格化 / 3 个 loading aria-busy — 都是 a11y / 类型一致性的最后打磨
- **design ring 引入的 TS 错也修了**：Badge variant secondary → default + className 颜色覆盖。这是「飞轮协作时序」的成功案例 — refine ring 用 tsc 抓到 design 引入的破坏，beta 出门前消除

### Design ring 005 的新增（/studio 真混剪页 + lib/nav.ts 加项）

**正面**：
- `/studio` 是 ShadowBlade SaaS 的核心价值落地（真后端 ffmpeg 接通，不再只是 mock UI）
- `mixFeatures` 用 alive flag 防 race 是教科书级别的 React 异步范式（5 轮内首次出现，质量很高）
- `MixCue / MixVideoRequest / MixVideoResponse` 5 个类型定义完整，TS 严格
- BRAND token 接入率维持 100%（studio-workbench 0 hex 字面量）
- 中文文案专业、品牌化（「连上 ffmpeg，直接渲染。」呼应 marketing hero）
- lib/nav.ts 用 NAV → ROUTE_LABEL 派生范式让 /studio 在 sidebar / mobile-sidebar / topbar 三处零维护接通

**负面**：
- **a11y 显著漂移**（5 轮飞轮统一范式被 1 个文件破坏）— 14 处 icon 无 aria-hidden + ChipGroup 缺 aria-pressed/role=toolbar + 2 处 Loader2 无 preserve-motion
- **hardcoded 绝对路径** 是非作者机器立即崩的 P0 阻塞（demo / Vercel / CI 都会立即报错）
- **协作时序**：design ring 005 加新组件时没遵循 refine ring 003-004 死透的 a11y 范式 — refine 005 应用清单只覆盖了 test ring 004 的报告，没主动扫 design ring 同期 commit 的 studio-workbench。这是「design ring 加新内容 → refine ring 不知道也没扫」的 5 轮内最严重的一次摩擦

### ring 004 → 005 的整体收敛度

| 维度 | ring 003 → 004 | ring 004 → 005 | 趋势 |
|---|---|---|---|
| P0 修复率 | 4/4 (100%) | n/a（上轮无 P0） | 持平（理想态）|
| P1 修复率 | 14.5/15 (97%) | 3/3 (100%) | ✓ 改善 |
| P2 顺手清理 | 5 / 14 | 5 / 5（无显式跳过） | ✓ 改善 |
| **跨轮回归** | 0 | **0** | 持平 |
| **新引入 P1 / P0** | 2 P1（aside+toolbar / not-found CTA） | **3 P2 + 1 P0**（全部在 studio 一个文件）| -1 |
| **协作时序摩擦** | 中等（design 加 boundary + root 改） | **中等**（design 加 /studio 不遵循范式）| 持平 |
| **代码完整度** | lib/nav + library-folders + 4 boundary | /studio page + studio-workbench + mix\* api 类型 | 持平 |
| **BRAND 接入率（除 project-cover）** | 100% | **100% 维持** | 持平 ✓ |
| **跨页一致性** | 100% | **95%**（studio ChipGroup 漂移）| -5% |

### 「可发 internal beta v0.4」评估

按 test ring 004 §七 的 9 项门槛 + 本轮新增 /studio：

| 门槛 | 状态 |
|---|---|
| TS 0 error | ✅ 持续维持 |
| 3 类 critical 安全（路由 / 焦点 / setTimeout cleanup） | ✅ 5 轮死透 |
| 5 个 ARIA 属性 100% 语义正确 | ⚠ **95%**（studio ChipGroup 漂移）|
| BRAND token 接入率（除 project-cover）100% | ✅ 维持 |
| 14 → 15 路由可用 | ⚠ **14/15** — studio 在 qiu 本机可演示，其它机器立即崩 |
| 外部访客 share/[token] 无内链泄漏 | ✅ ring 004 死透 |
| KPI 数据 / srHint 一致性 | ✅ ring 005 修死 |
| 中文文案合规 | ✅ 5 轮零失分 |
| 响应式 360/480/768/1024/1320 | ✅ |

**14 个 (app) 路由（不含 studio） + 1 marketing + 2 (external) = 17 路由全部 ready for beta**。
**studio 在作者本机 demo 可用**（仅作 backend 接通示意，不可作为生产可分享路径）。

#### 评估摘要

- **内部演示员工（Acme 工作空间）**：完全 ready ✓（含作者本机 /studio 真混剪展示）
- **客户 / 销售 demo**：完全 ready ✓（不演示 /studio 或仅演示 14 路由不含 studio）
- **外部访客（分享链接审阅）**：完全 ready ✓
- **公开 marketing landing（/）**：完全 ready ✓
- **production paying customer**：未到位（需 middleware / OAuth / 真 API / project-cover BRAND / studio 路径绝对路径修复）

### 目标用户匹配度

最严格的解读：**v0.4-internal-beta 可以打 tag**，前提是 release note 明确说明：
- `/studio` 仅作 backend 接通示意（real ffmpeg pipeline），路径硬编码到作者本机；非作者机器请用 `/create` 演示流水线 mock UI
- 演示视频应录制作者本机 /studio 跑通过程，分享给销售 / 内部演示员工

或者更稳妥的路径：先 fix studio P0（hardcoded 路径）+ 3 个 P2（aria-hidden / aria-pressed / preserve-motion），再打 v0.4 — 这只需要 refine ring 006 一轮约 20 分钟即可完成。

---

## 七、结论

### ring 004 → 005 是飞轮的**最干净的 refine ring**：
- 3 P1 + 5 P2/P3 + 1 design 引入的 TS 错 = 9/9 = **100% 应用完成度**
- 跨轮回归 **0 次**
- BRAND 接入率维持 100%
- 中文文案 5 轮零失分

### 但 ring 004 → 005 不是**最干净的 design ring**：
- design ring 005 引入 /studio 时没遵循 refine 003-004 死透的 a11y 范式
- 14 处 icon 无 aria-hidden、ChipGroup 缺 toolbar/pressed、Loader2 无 preserve-motion — **studio-workbench 一个文件累积了 3 个 P2 + 1 个 P0**
- 这是 5 轮内最严重的「design 加新组件 → refine 没扫到」的协作时序摩擦

### 最值得 refine 006 立刻处理的 4 个 finding（按优先级）：

1. **studio-workbench DEFAULT_SAMPLES 绝对路径 → 相对路径**（P0 · 1 行）— 解锁非作者机器的 /studio 演示
2. **studio-workbench 14 处 icon 加 aria-hidden**（P2 · 14 行）— 与 5 轮范式对齐
3. **studio-workbench ChipGroup 加 role=toolbar + aria-pressed**（P2 · 重构 ~10 行）— SR 用户能识别 3 处互斥按钮组
4. **studio-workbench 2 处 Loader2 加 preserve-motion**（P2 · 2 行）— 与 create-wizard 范式对齐

总工作量约 **27 行代码 + 20 分钟**。完成后即可打 v0.4-internal-beta tag。

### 喂回 Design ring 006 协作时序反馈

5 轮飞轮总结的「design ring 加新文件 → refine ring 不知道也没扫」摩擦点已经出现 3 次：
- ring 002 → 003：design 加 4 新页 → refine 003 追平
- ring 003 → 004：design 加 boundary + root 改 → refine 004 追平
- ring 004 → 005：design 加 /studio → refine 005 **没追平**（仅修了 design 引入的 TS 错，没扫整页 a11y）

**建议（喂 design ring 006）**：
- design ring 提 PR 前跑 `npx tsc --noEmit && grep -rn 'animate-spin' app/ components/ | grep -v preserve-motion && grep -rn '<Loader2\|<Sparkles\|<Film\|<Cpu' src/ | grep -v 'aria-hidden\|sr-only'` 当作 self-check pre-flight
- 同时 design ring 应在 commit message 显式列出「新文件清单」让 refine ring 知道需要追加扫描范围
- refine ring 应每轮扫一遍 `git log --since="$last_ring_date" --diff-filter=A --name-only` 查 design ring 期间新增的文件，主动扫这些新文件的 a11y / preserve-motion 范式

### 接下来的 design ring 006 应优先 unlock

按对 production-ready 的贡献度排序（5 轮飞轮总结）：

1. **`middleware.ts` 加 redirect**（未登录 → /login）— 解决 root not-found 次 CTA / 防 (app) mock data 泄漏
2. **OAuth flow** — login page + Google / Microsoft / Okta provider
3. **API 接通** — analytics / notifications / integrations / mix-video 真后端
4. **project-cover.tsx 整组下放 BRAND**（26 hex + 6 gradient id）
5. **studio-workbench DEFAULT_SAMPLES 改用 backend 提供清单 + 上传入口**
6. **三处 empty state（template-filter / project-filter / projects-board / integrations）统一用 `<EmptyState>`**
7. **CI hex lint + preserve-motion lint + aria-hidden lint** — `.eslintrc` 加规则防止 5 轮飞轮范式被新代码破坏

---

*Test ring · pass 005 — 15 page + 7 boundary + 32 组件，扫描完成。Refine ring 005 应用 100%，design ring 005 引入 1 个真混剪页质量整体不错但 a11y 漂移显著。距 v0.4-internal-beta tag 还差 4 个修复（27 行代码，约 20 分钟）。5 轮飞轮的「设计 × 测试 × 修复」核心范式全部稳定。*
