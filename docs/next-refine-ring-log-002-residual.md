# ShadowBlade Next.js · Refine Ring Log 002（残余补丁）

Refine 日期：2026-05-21
Refine 员：Refine ring · pass 002（test ring 002 残余补丁）
输入：[`next-test-ring-report-002.md`](./next-test-ring-report-002.md)（3 P0 + 11 P1 + 21 P2）
范围：`frontend-next/`，仅本轮其他 pass 未触动的残余 P1

---

## 上下文与文件命名说明

本仓库的 refine 飞轮在并行推进，test ring 002 的 P0 / P1 / P2 已经被 `cd6579f`（"apply test ring 002 pass · P0 race + a11y"）+ `cd6579f`（"apply test ring 003 pass · NAV 接通 + 新页 vibe + a11y"）+ `5becd46`（"apply test ring 004 pass · 3 P1 一行 fix"）三轮 commit 累积应用，对应日志：

- `docs/next-refine-ring-log-002.md`（先前批次 · vibe-Bug 应用，不是 test ring 002）
- `docs/next-refine-ring-log-003.md`（test ring 002 第一轮，2 P0 + 15 P1，应用 createWizard cleanup / mobile-sidebar focus-trap 等）
- `docs/next-refine-ring-log-004.md`（test ring 003，4 P0 + 15 P1，应用 NAV / share VideoPlayer 复用 / analytics figcaption 等）
- `docs/next-refine-ring-log-005.md`（test ring 004，3 P1 一行 fix）

本文件（log-002-residual）记录的是上述三个 commit 之后，对 `next-test-ring-report-002.md` 仍未应用的 4 项残余 P1，不重复编号（避免与已有日志冲突）。

---

## 应用清单

### test ring 002 P0 · 3/3 已由先前 pass 应用 ✓

- P0.1 integrations search + tab 不正交（`integrations:57-61`）— 由 cd6579f 修，filter 拆"先按 tab、再按 q"两步 ✓
- P0.2 share/[token] 双 aria-label 重复（`share/[token]:150-161 + 163-171`）— 由 cd6579f 修，整段 SVG 替换为 `<VideoPlayer watermark="DRAFT · v17" />` ✓
- P0.3 analytics 柱图 `<div aria-label>` SR 不读（`analytics:116-117`）— 由 cd6579f 修，包 `<figure>` + sr-only `<figcaption>` 给完整 7 天数据描述 ✓

### test ring 002 P1 · 本轮新落地 4 项

| # | 报告条目 | 做了什么 |
|---|---|---|
| P1.13 | `app/page.tsx` `redirect("/dashboard")` 让外部访客踩进 (app) | 把 `redirect` 替换为极简 marketing hero：BrandMark + h1「一份简报，四分钟出片」+ 3 个 feature 卡 + footer。员工点「进入工作台」CTA 走 /dashboard；外部访客（share/[token] 的 logo / footer 链接已在 cd6579f 改成 https://shadowblade.io/）从这里入门时不再被无意带入 (app) layout。是 RSC，0 JS。 |
| P1.14 | root layout 缺 `metadataBase` | 加 `metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://frontend-next-two-lac.vercel.app")`；不再触发 build 时 `metadata.metadataBase is not set` warning；OG image `/og-image.svg` 现在能解析为绝对 URL，社交 unfurl 不再坏。 |
| P1.12 | `app/not-found.tsx` 未跟随 route group 拆 | 新增 `app/(app)/not-found.tsx`：保留「返回工作台 / 项目库」双 CTA（员工视图）；`app/not-found.tsx` 已由 5becd46 改成单 CTA「回到首页」（中立 fallback）。route group 各自分支 OK。 |
| 特殊检查 A | (external) 缺 not-found boundary | 新增 `app/(external)/not-found.tsx`：「链接失效」单页文案，无内链跳工作台，符合外部访客语义（cf. test ring 002 维度十 warn）。`(external)/loading.tsx` 由 5becd46 已落地。 |

### 顺手修的工程债（不在 test ring 002 报告中，但阻塞 build）

| # | 现象 | 做了什么 |
|---|---|---|
| build · kpi-tile "use client" + Lucide icon prop | refine 004 给 KpiTile 加 "use client" 后，server 父组件（dashboard / team / analytics）传 `icon: LucideIcon` 触发 Next.js 14「Functions cannot be passed to Client Components」prerender 报错。`npm run build` 失败。 | 删 KpiTile 顶部 `"use client"`；`useId` 在 server / client 两端都可用，无需 client directive。注释说明：未来如真要 client 化（比如加 useState），需配合 icon prop API 改造（如改成接受图标名字符串而非函数）。 |

---

## 跳过 / 留给后续

| 项 | 原因 |
|---|---|
| test ring 002 P1.4「share/[token] 整页 client 299 行拆 server」 | 当前 share 因 4 个 useState（playing / decided / copied / draft）仍是整页 client。cd6579f 已通过 `<VideoPlayer />` + `<BrandMark />` 复用减了 ~70 行 SVG；进一步拆 `<SharePlayer />` `<DecisionPanel />` `<CommentThread />` 三个 client island 需要重新审视 page 主体的 data flow，留 design v5 决定。 |
| test ring 002 P2 类（21 项） | 由先前 pass 累计已应用大部分；剩余在 refine ring 003 / 004 / 005 跳过队列中明确登记。 |

---

## 验收

- `cd frontend-next && rm -rf .next && npm run build` → 0 错 ✓
- 16 路由全部成功生成（含新增的 `/studio` + 现有 15 路由） ✓
- Route table size sanity：`/`（1.11 kB） / `/analytics`（163 B server only） / `/share/[token]`（9.81 kB client） — 形状对得上预期 ✓
- 无 `metadataBase` build warning ✓

文件触动：

- 新增（3 个）：
  - `app/(app)/not-found.tsx`（员工视图 404 · 双 CTA「返回工作台 / 项目库」）
  - `app/(external)/not-found.tsx`（外部访客 404 · 单文案「这个分享链接不存在」）
  - `docs/next-refine-ring-log-002-residual.md`（本文件）

- 编辑（3 个）：
  - `app/page.tsx`（redirect → marketing hero）
  - `app/layout.tsx`（+ metadataBase）
  - `components/workspace/kpi-tile.tsx`（- "use client"，加注释防回归）

---

## 与并行 refine pass 的关系

本轮跑得相对靠后，发现 cd6579f / ce098de / 5becd46 三个 commit 已经把 test ring 002 的 P0 + 大部分 P1 + 顺带 test ring 003/004 都做完。本轮专注 4 项残余 P1 + 1 项 build 阻塞 fix。

下一轮 refine 拿到 test ring 005（如有）时，应该看到本轮残余补丁已落地，不再出现：
- 「`/` redirect 让外部访客踩进 (app)」
- 「metadataBase 缺失 build warning」
- 「(app) / (external) loading + not-found 形状不分」
- 「KpiTile 标 client 阻塞 server 父传 Lucide icon」

---

*Refine ring · pass 002（残余补丁）— 4 项 test ring 002 P1 + 1 项 build 阻塞 fix。test ring 002 整轮（3 P0 + 11 P1）由本批 + 前序 3 个 commit 共同完成应用。*
