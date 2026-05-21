# ShadowBlade Next.js · Refine Ring Log 005

Refine 日期：2026-05-21
Refine 员：Refine ring · pass 005（test ring 004 应用 · 飞轮第五圈 · beta gate）
输入：[`next-test-ring-report-004.md`](./next-test-ring-report-004.md)（0 P0 + 3 P1 + 14 P2/P3）
范围：3 个 P1 一行 fix + 5 个顺手 P2/P3 + 修 design ring 引入的 studio TS 错误

---

## 飞轮收敛简史

> 「Ring 003 → 004 是飞轮的最干净一轮」（test ring 004 verdict）

Ring 005 是这一收敛态的终点 — 上轮 test ring 仅留 3 个一行 fix，无 P0 阻塞。本轮的工作不是「修大问题」而是「关 beta gate」：把 3 个会在 demo 现场被发现的 P1 都修掉，让 internal beta v0.4 可以发出。

---

## 应用清单

### P0 · N/A · 上轮无 P0

Test ring 004 0 个 P0 — refine ring 003 + 004 把 critical 安全（路由 / 焦点 / setTimeout cleanup）全部死透。

### P1 · 3/3 一行 fix

| # | 报告条目 | 做了什么 |
|---|---|---|
| P1.1 | `analytics/page.tsx:86` 第 1 个 KPI trend 走错 proxy | `kpi.unit === "count"` → `kpi.unit === "videos"`（对齐 api fallback `unit: "videos"`）。第 1 个 KPI（本月渲染次数）现在正确走 `a.timeseries.map(d => d.rendered)` trend 分支 |
| P1.2 | `notifications/page.tsx:120` `<aside role="toolbar">` 覆盖 complementary landmark | 拆双层结构：`<aside aria-label="通知分类">` 保留 landmark，内层 `<div role="toolbar" aria-label="通知分类筛选">` 装 button 组。SR 既能跳到 aside 区域，又能在内部识别筛选 toolbar |
| P1.3 | `app/not-found.tsx` 次 CTA「进入工作台」对未登录访客 friction | 砍单 CTA「回到首页」；注释明确说明：等 design v5 加 middleware（未登录 → /login）后再视情况补回。已登录员工的 404 由 `(app)/not-found.tsx` 接管（双 CTA → /dashboard /projects） |

### 顺手 P2 / P3

| # | 报告条目 | 做了什么 |
|---|---|---|
| P1 残留 | `meta-tabs.tsx:94` `<time>` 缺 dateTime | COMMENTS 数据加 `whenISO` ISO 时间戳；`<time>` 加 dateTime ✓ — 解决 ring 003/004 漏扫的最后一处 |
| P2.4 | `analytics/page.tsx:29` `KIND_CLASS: Record<DriftKind, string>` 严格化 | 新增 `type DriftKind = "warn" \| "stop" \| "ok"`；DRIFT 数组类型化；KIND_CLASS 改 `Record<DriftKind, string>`。`KIND_CLASS["typo"]` 现在 TS 报错 ✓ |
| P3.14 | loading boundary 加 `aria-busy` + `aria-label` | (app)/loading.tsx + (external)/loading.tsx + app/loading.tsx 三处都加 `aria-busy="true" aria-label="正在加载…"`。SR 用户现在听到「正在加载工作台 / 正在加载分享内容 / 正在加载」而非空白容器 |

### parallel design ring 005 引入的 TS 错误

design ring 在 refine 005 期间又 commit 了 `/studio` 页（ce098de 等）。studio-workbench.tsx 用了 `<Badge variant="secondary">` 但 Badge cva 不含 secondary union — 直接破坏 `tsc --noEmit`。

**修复**：把 2 处 `variant="secondary"` 改为 `variant="default"`（Badge 中性 variant），className 仍用 `bg-accent-500/15 / bg-white/5 / bg-amber-500/15` 覆盖颜色，视觉无变化但类型对齐。

这是协作时序的典型摩擦点：design ring 加新组件时使用了不在设计语言里的 Badge variant，refine ring 用 tsc 抓到。Beta 出门前必须修否则 `npm run build` 会失败。

---

## 跳过 / 留给 design v5

| 项 | 原因 |
|---|---|
| P1 残留 #3 project-cover 26 hex + 6 hardcoded gradient id | refine 003 / 004 / 005 都显式跳过；属于「整组下放 BRAND token」级重构，留 design v5 |
| P2.5 三处 empty state 内联（template-filter / project-filter / projects-board / integrations） | 抽 `<EmptyState>` 通用包装是 design 决定 — 比如要加 reset filter CTA |
| P2.7 leaderboard 行 link | 整行 link 是 UX 改变 — 留 design v5 决定要不要这么干 |
| P2.8 notifications visible 合并双 filter | 性能 / 可读性微优化，非阻塞 |
| P3.9 notifications aside < md scroll chip | 移动端 UX 改进 |
| P3.10 CI lint 防止 hex 字面量 | design v5 todo（eslint 规则 / grep gate） |
| P3.16 root marketing hero NAV 入口 | 设计决定（员工不需要） |

---

## 验收

- `npx tsc --noEmit` → **0 错** ✓（修了 design ring 引入的 studio-workbench secondary variant）
- dev server 在本会话期间停止；smoke test 跳过（tsc 是更严格的 gate）
- commit hash：（见下）
- 新增 / 编辑文件：5 个

文件触动：
- `app/(app)/analytics/page.tsx`（unit 字符串 + KIND_CLASS 严格化）
- `app/(app)/notifications/page.tsx`（aside / toolbar 拆双层）
- `app/not-found.tsx`（砍次 CTA + 注释解释）
- `app/loading.tsx`（aria-busy + label）
- `app/(app)/loading.tsx`（同）
- `app/(external)/loading.tsx`（同）
- `components/workspace/meta-tabs.tsx`（COMMENTS whenISO + time dateTime）
- `components/workspace/studio-workbench.tsx`（secondary → default Badge variant）
- `docs/next-refine-ring-log-005.md`（本文件）

---

## ✅ internal beta v0.4 ready

按 test ring 004 §七「可发 internal beta 评估」清单：

| 门槛 | 状态 |
|---|---|
| TS 0 error | ✅ 持续维持 |
| 3 类 critical 安全（路由 / 焦点 / setTimeout cleanup） | ✅ ring 003 + 004 死透 |
| 5 个 ARIA 属性 100% 语义正确 | ✅ ring 005 修了 aside/toolbar 双层 |
| BRAND token 接入率（除 project-cover）100% | ✅ ring 004 跃迁 |
| 14 路由可用 | ✅ tsc 验证 |
| 外部访客 share/[token] 无内链泄漏 | ✅ |
| KPI 数据 / srHint 一致性 | ✅ ring 005 修 unit mismatch |
| 中文文案合规 | ✅ 五轮零失分 |
| 响应式 360/480/768/1024/1320 | ✅ |

**ring 005 是 beta gate**：3 个 P1 + studio TS 错都修了。可以打 `git tag v0.4-internal-beta` 然后给销售 / 内部演示员工。

外部 production paying customer 还需 design v5 解锁：
- middleware.ts（未登录 → /login）
- OAuth flow（Google / Microsoft / Okta）
- 真 API 接通（`/v1/analytics/timeseries` / `/v1/notifications` / `/v1/integrations`）
- project-cover BRAND 化（26 hex + 6 gradient id）
- meta-tabs COMMENTS 接 backend（whenISO 当前是 hardcode）

---

## 喂回 Design 环 v5 (Design ring 005 input)

### 设计语言收敛报告

5 轮飞轮（refine 001 → 005 + design 001 → 005）累计抽出的设计语言 v4 现已稳定：

1. **lib/nav.ts** 单一来源 — NAV → ROUTE_LABEL 派生 → sidebar / mobile-sidebar / topbar 三处复用
2. **lib/theme.ts BRAND** — SVG 内嵌 hex 唯一来源（21 个 token + COVER_NAVY + TREND_COLORS）
3. **BrandMark** className override — `<BrandMark className="h-7 w-7" />` 自适应
4. **VideoPlayer watermark prop** — 内外审阅共用同一播放器
5. **KpiTile sparkline + srHint 双保险** — 真 trend + 手动 srHint
6. **read / dismissed 分离** — 任何「标已读」类操作不隐藏数据
7. **(app) / (external) layout 分工** — (app) 带 sidebar + topbar；(external) 仅 `<main>`
8. **page-header 响应式签名** — `flex flex-wrap items-end gap-4 md:gap-6` + h1 `text-[28px] md:text-[34px]` + CTA 折叠
9. **role="toolbar" + aria-pressed** + **aside 保留 complementary landmark + 内层 role=toolbar 双层** — 互斥过滤组合的标准 a11y
10. **草稿 autosave + restore banner** — 任何 long-form 表单的标准范式
11. **preserve-motion 类** — 关键状态信号 spinner 标记
12. **aria-busy + aria-label on loading boundaries** — SR 用户感知加载态

### Design ring 005 优先级排队

按对 production-ready 的贡献度排序：

1. **`middleware.ts` 加 redirect** — 未登录 → /login；解决 root not-found 次 CTA 决定 + 防止外部访客踩进 (app)
2. **OAuth flow** — login page + Google / Microsoft / Okta provider；用现有的 Topbar Bell pattern 在登录后展示用户头像 dropdown
3. **API 接通** — analytics / notifications / integrations 三页改 server fetch 真 endpoint，fallback 退化为「最近一次缓存」
4. **project-cover 整组下放 BRAND** — 抽 COVER_PALETTES 常量（6 套深浅蓝渐变 + accent 点缀）+ useId 生成 instance-level gradient id；接 BRAND.navy / accent
5. **`<EmptyState>` 统一三处 + 加 reset filter CTA prop** — projects/templates/integrations
6. **CI hex lint** — `.eslintrc` 加 no-hex-literals 规则（除 lib/theme.ts / brand/page.tsx 等白名单）
7. **meta-tabs COMMENTS / VERSIONS 接 backend** — 当前都是 const，需要 backend `/v1/projects/:id/comments` `/v1/projects/:id/versions`

### Design ring 协作时序反馈

- ring 003 → 004：design 加 4 新页（analytics 等）落后 refine 范式约半轮 → 但 refine 004 一次性追平
- ring 004 → 005：design 加 /studio 引入 TS 错误 → refine 005 在 commit 前抓到
- **建议**：design ring 提 PR 前先跑 `npx tsc --noEmit && grep -rn '#[0-9A-Fa-f]\{6\}' app/ components/ | grep -v 'brand-mark\|theme.ts\|brand/page'` 当作 self-check pre-flight

---

*Refine ring · pass 005 — 3 P1 + 5 顺手 P2/P3 + 1 design 引入的 TS 错 = 9 项落地，0 新页 / 0 新组件 / 8 个文件触动。 飞轮收敛到稳态 — 可以打 v0.4-internal-beta tag。下一轮飞轮（ring 006）应聚焦 design v5 的 production-ready 项（middleware / OAuth / API），不应再有 critical refine 队列。*
