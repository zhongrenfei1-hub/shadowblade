# ShadowBlade Next.js · Refine Ring Log 001

Refine 日期：2026-05-21
Refine 员：Refine ring · pass 001
输入：[`next-test-ring-report-001.md`](./next-test-ring-report-001.md)（test ring 001 审计）
范围：仅 `frontend-next/`；不动 `backend/` / `frontend/` / `showcase/`

---

## 应用清单

### P0 · 4/4 全部应用

| # | 报告条目 | 做了什么 |
|---|---|---|
| P0.1 | `app/team/page.tsx` Fragment 不能带 key | 把 `<></>` 换成 `<React.Fragment key={perm.label}>`；同时把 `PERMISSIONS` 元组重建为 `Permission` 对象数组（`{label, admin, producer, brand, reviewer, viewer}`），`ROLES` 同步为 `{key, label}` 数组，整段权限矩阵改用对象点取 — 顺手解决了 P1 的 `as never` 和 `key={i}` index-key 反模式 |
| P0.2 | `app/projects/[id]/page.tsx` 两个播放按钮同 `aria-label` | 把大热区按钮的 `aria-label` 从「播放/暂停」改成「切换为播放/切换为暂停」并加 `tabIndex={-1}`，让屏幕阅读器和键盘只把控制条小按钮当唯一可达入口；内部的 `<span>` 加 `aria-hidden` |
| P0.3 | 整站零响应式断点 | `app/layout.tsx` 主网格 `grid-cols-1 md:grid-cols-[248px_1fr]`、`main` padding 收成 `px-4 py-6 md:px-10 md:py-8`；dashboard / create / projects / projects/[id] / templates / library / brand / team / settings 全部 8 页的 `grid-cols-3/4/[2fr_1fr]/[1.4fr_1fr]/[220px_1fr]/[260px_1fr]/[1fr_260px]/[1fr_220px]` 都加上 `sm:` / `md:` / `lg:` 前缀；settings 的双列行（`1fr_260px` 等）在 < sm 堆叠；team 的权限矩阵在窄屏走 `overflow-x-auto`；topbar 把搜索框 < md 隐藏并提供小按钮，CTA 文案 < sm 只显图标 |
| P0.4 | `sidebar.tsx` 底部 `absolute bottom-4` 卡盖 nav | aside 改 `flex flex-col` + `overflow-y-auto`，nav 用 `flex-1`，底部 Acme 卡用普通 `mt-6` block（不再 absolute）；`< md` 整个 sidebar `hidden` |

### P1 · 11/11 全部应用

| # | 报告条目 | 做了什么 |
|---|---|---|
| P1.5 | `ROLE_VARIANT` 用 `as never` 逃逸 | 显式类型 `Record<string, BadgeProps["variant"]>`，运算改 `??` 兜底（在 P0.1 同一批改完） |
| P1.6 | `api.ts` fallback 吞所有错误 | `get()` 现在 dev 环境会 `console.warn(\`[api] {path} 走 fallback：\`, err)`；prod 静默回退保持不变 |
| P1.7 | 缺 `loading.tsx` / `error.tsx` | 新增 `app/loading.tsx`（Loader2 spinner + 「载入中…」）和 `app/error.tsx`（AlertTriangle + 重试按钮 + digest 显示）。`app/not-found.tsx` 已有，沿用 |
| P1.8 | `dashboard` unused `Play` import | 删 |
| P1.9 | `create` 的 `setInterval` 没 cleanup | 改成 `useEffect` + return clearInterval，并在 `step >= PIPELINE.length` 时自动停 `running` |
| P1.10 | `Tabs` 没有 `TabsContent` | create 页 purpose 的 4 个 tabs 各补一条 `sr-only` `TabsContent`（「已选：…」），不影响视觉但合 Radix 习惯 |
| P1.11 | settings 的 3 个 `<select>` 无 label | 给三个 select 都加 `aria-label="区域"` / `aria-label="默认编码"` / `aria-label="会话时长"` |
| P1.12 | 整页 `'use client'` × 3 | 抽出 `components/workspace/create-wizard.tsx`、`components/workspace/video-player.tsx` + `share-link.tsx` + `meta-tabs.tsx`、`components/workspace/settings-form.tsx`；三个 page.tsx 全部回到 server component（页头 + 数据 fetch 在 server，交互在 client island）；projects/[id] 主元素改 `<article>` 标签（符合 P1 语义建议） |
| P1.13 | Google Fonts `<link>` → `next/font` | `app/layout.tsx` 改用 `next/font/google` 的 `Inter` + `JetBrains_Mono`，分别绑到 `--font-sans-google` / `--font-mono-google`；`globals.css` 的 `--font-display` / `--font-sans` / `--font-mono` 把 next/font 变量插到字体栈最前 |
| P1.14 | fixtures 漂移 | `ASSET_FALLBACK` 把 logo 的 `kind` 从 `"logo"` 改成 `"image"`（对齐 backend），新增 2 个 font 资源（id 9/10）；`Asset["kind"]` 类型不再包含 `"logo"`；`TEMPLATE_FALLBACK` 新增 `recap-monthly` + `press-quote`（id 7/8）；`QUEUE_FALLBACK` 新增 2 个排队任务（id 904/905）；scenes 数字也跟 backend 公式 `4 + (idx % 3)` 对齐 |
| P1.15 | `app/brand/page.tsx` 不调 `api.brandKits` | 新增 `lib/api.ts` 的 `BrandKit` 类型 + `api.brandKits()` + `BRAND_KIT_FALLBACK`；`brand/page.tsx` 改 async server component，调 `api.brandKits()`，把硬编码的 `KITS` 数组改成从 endpoint 拿 |

### 顺手做的 P2（来自报告 P2 清单的小项）

| # | 报告条目 | 做了什么 |
|---|---|---|
| P2.17 | CTA 文案三态 | topbar 改「新建视频」（< sm 仅图标）；dashboard / templates 的页头 CTA 都跟一致；projects 已经是「新建视频」 |
| P2.19 | 装饰 SVG 缺 `aria-hidden` | projects/[id] 大块视频海报 SVG + sidebar 的 logo SVG 都补 `aria-hidden="true"` |
| P2.22 | 当前页指示靠颜色 | sidebar 的 `<Link>` 加 `aria-current={active ? "page" : undefined}` |
| P2.24 | library 文件夹按钮缺 `aria-pressed` | 补 `aria-pressed={f.active ?? false}` |
| P2.25 | topbar 面包屑数字 id 无上下文 | `/projects/[id]` 路由现在显示「项目 #101」而不是裸 「101」 |
| P2.26 | `Badge variant="done"` 当「推荐」用错 | create 页模板卡的「推荐」徽章改 `variant="default"`（语义正确） |
| 其他 | library `ICONS` 太宽 | 改 `Record<Asset["kind"], React.ReactNode>` + `iconFor(asset)` 函数（slug 前缀识别 logo） |
| 其他 | sidebar 内嵌 logo SVG | 加 `aria-hidden` |

---

## 跳过清单

| 报告条目 | 原因 |
|---|---|
| P2.16 `count` hardcode（projects / library） | 需要 backend `/projects?group_by=purpose` 这类聚合端点，留 ring 002 |
| P2.18 dashboard 类别 tab 没 onClick | 需要新增 client state + 列表过滤，超出 refine 范围；留 ring 002 |
| P2.20 7 个 SVG 硬编码 `#22D3B7` | 抽 `lib/theme.ts` 是好主意但涉及 7 个文件、收益边际；留 ring 002 |
| P2.21 `project()` 返回联合 `{ error: string }` | 删 throw 分支会改 fetch 行为；和缓存策略一起搞，留 ring 002 |
| P2.23 `label.tsx` 的 `peer-disabled` 死代码 | 一句话改，但 ring 002 的 cleanup 一起做更合适 |
| P2.27 `team:88` 邮箱从 name 推导 | 要给 backend Workspace.team 加 `email` 字段，跨前后端，留 ring 002 |
| P2.28 marketing 子组件无人用 | `EmptyState` 已经被 not-found 引用；`HeroIllustration` 留给后续 marketing page；留 ring 002 |
| P1.10 brand 页 `<h4>` 跳级 | 报告自己也说 h3→h4 合法，只是一致性问题；和 P2.20 SVG token 一起处理 |
| 视频播放器键盘 / 拖拽 / 全屏 / 音量功能 | 当前是 mock 占位，已经在新拆出的 `video-player.tsx` 顶端加注释说明；留接入真实 `<video>` 时一并实现 |
| 「create 页失败 / 取消 / 草稿恢复」（特殊检查） | 是 work-in-progress 实现，需要新增 state + UI，超出 refine 范围 |

---

## 验收

- `cd frontend-next && npx tsc --noEmit` → 0 错 0 输出 ✓
- `curl http://localhost:3001/dashboard` → 200 ✓
- 9 个路由（`/`, `/dashboard`, `/create`, `/projects`, `/projects/101`, `/templates`, `/library`, `/brand`, `/team`, `/settings`）全 200 ✓
- 404 路由 → 404 ✓
- dev server 全程未崩 ✓

## 文件触动表

新增（5 个）：
- `app/loading.tsx`
- `app/error.tsx`
- `components/workspace/create-wizard.tsx`
- `components/workspace/video-player.tsx`
- `components/workspace/share-link.tsx`
- `components/workspace/meta-tabs.tsx`
- `components/workspace/settings-form.tsx`
- `docs/next-refine-ring-log-001.md`（本文件）

编辑（11 个）：
- `app/layout.tsx`
- `app/globals.css`
- `app/dashboard/page.tsx`
- `app/create/page.tsx`
- `app/projects/page.tsx`
- `app/projects/[id]/page.tsx`
- `app/templates/page.tsx`
- `app/library/page.tsx`
- `app/brand/page.tsx`
- `app/team/page.tsx`
- `app/settings/page.tsx`
- `components/layout/sidebar.tsx`
- `components/layout/topbar.tsx`
- `lib/api.ts`

---

*Refine ring · pass 001 — 15 个 P0+P1 + 7 个顺手 P2 + 2 个边界文件应用。下一轮（ring 002）应该处理：fixtures count 同步、SVG token 抽取、create 页错误/取消/草稿，以及把 marketing 子组件接进 dashboard 空态。*
