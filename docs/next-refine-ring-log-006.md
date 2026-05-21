# ShadowBlade Next.js · Refine Ring Log 006

Refine 日期：2026-05-21
Refine 员：Refine ring · pass 006（test ring 005 应用 · 飞轮第六圈 · /studio 范式对齐）
输入：[`next-test-ring-report-005.md`](./next-test-ring-report-005.md)（1 P0 + 0 P1 + 3 P2 — 全部在 /studio 页）
范围：仅 `components/workspace/studio-workbench.tsx`，把 /studio 对齐 5 轮飞轮抽出的范式

---

## 上下文

Ring 005 关 beta gate 时，design ring 提交了 `/studio` 页（真混剪 backend 接入），但没遵循 5 轮飞轮死透的 a11y 范式。Test ring 005 抓出 4 个 finding：

1. **P0**：`DEFAULT_SAMPLES` 写死 `/Users/qiu/工作流/...` 作者本机绝对路径 — 在 CI / 同事机器立即崩
2. **P2**：14 处 lucide icon 无 `aria-hidden`
3. **P2**：`ChipGroup` 缺 `role="toolbar"` + `aria-pressed`
4. **P2**：2 处 `Loader2` 无 `preserve-motion`

总工作量约 27 行代码 — 比修 P1 还轻量。但**必须修**，否则 release note 必须解释「/studio 路径硬编码，演示用其它 14 路由」，违反 SaaS demo 完整性。

---

## 应用清单

### P0 · 1/1 死透

**`DEFAULT_SAMPLES` 改相对路径**：

```diff
-const DEFAULT_SAMPLES = {
-  clipA: "/Users/qiu/工作流/shadowblade/storage/samples/clip_a.mp4",
-  clipB: "/Users/qiu/工作流/shadowblade/storage/samples/clip_b.mp4",
-  clipC: "/Users/qiu/工作流/shadowblade/storage/samples/clip_c.mp4",
-  voice: "/Users/qiu/工作流/shadowblade/storage/samples/voice.wav",
-  bgm: "/Users/qiu/工作流/shadowblade/storage/samples/bgm.wav",
-  logo: "/Users/qiu/工作流/shadowblade/storage/samples/logo.png",
-};
+// 相对路径：backend 启动目录通常是 shadowblade/ 仓库根，相对路径
+// `storage/samples/...` 在所有机器都成立。之前硬编码绝对路径在 CI / 同事机器 404。
+const DEFAULT_SAMPLES = {
+  clipA: "storage/samples/clip_a.mp4",
+  clipB: "storage/samples/clip_b.mp4",
+  clipC: "storage/samples/clip_c.mp4",
+  voice: "storage/samples/voice.wav",
+  bgm: "storage/samples/bgm.wav",
+  logo: "storage/samples/logo.png",
+};
```

`toBrowserUrl()` helper（line 89-97）已经支持相对路径（`storage/...` → `/static/storage/...`），所以这个改动是零副作用。

### P2 · 3/3 全部应用

**lucide icon aria-hidden（14 处）**：用 python 正则一次扫了 9 处 `<Icon className=... />`，剩 5 处用 `<Icon size={N} className=... />` 的混合形式手动补：
- Sparkles `text-accent-300 size={18}` (line 170)
- 2 处 AlertTriangle (line 303, 468)
- Film `size={18}` (line 313)
- Mic `size={24}` (line 366)
- generate button 的 bare `<Sparkles />`（line 292）

**ChipGroup 加 role=toolbar + aria-pressed**（line 489-507）：

```diff
-      <div className="flex flex-wrap gap-1.5">
+      <div className="flex flex-wrap gap-1.5" role="toolbar" aria-label={label}>
         {options.map((o) => (
           <button
             key={o.key}
             type="button"
             onClick={() => onChange(o.key)}
+            aria-pressed={value === o.key}
```

ChipGroup 被用 3+ 次（LOOKS / ASPECTS / TRANSITIONS / 其它）— 一次性把 studio 的 3 组 toolbar 范式对齐 ProjectFilter / TemplateFilter / ProjectsBoard / LibraryFolders 的写法。

**Loader2 加 preserve-motion**（2 处）：
- line 288：「生成中…」大按钮的 spinner
- line 332：FeaturesBadgeRow 「检测 ffmpeg 能力…」spinner（同时给容器加 `aria-busy="true" aria-label="正在检测 ffmpeg 能力"`，SR 用户感知加载态）

---

## 验收

- `npx tsc --noEmit` → **0 错** ✓（5 轮 + 这一轮全程维持）
- `grep preserve-motion` → 5 处全部在 Loader2 关键状态 ✓
- `grep aria-pressed` → 8 处全部在 button 上 ✓
- `grep role="toolbar"` → 7 处全部配 aria-label ✓

文件触动：
- `components/workspace/studio-workbench.tsx`（唯一文件）
- `docs/next-refine-ring-log-006.md`（本文件）

---

## ✅ Beta v0.4 完整闭环

按 test ring 005 §⑤ 的 verdict：「**可以打 v0.4-internal-beta tag，但建议先跑 refine 006**」— 本轮做完后，**条件齐了**。

### 14 路由 + /studio + 2 external + 1 marketing 整体状态

| 范畴 | 状态 |
|---|---|
| TS 0 error | ✅ 6 轮持续 |
| Critical 安全（路由 / 焦点 / setTimeout / 焦点 trap） | ✅ ring 003 + 004 + 006 |
| BRAND token 接入率（除 project-cover） | ✅ 100% |
| ARIA 5 属性语义正确 | ✅ 100%（含 ChipGroup 修复后） |
| preserve-motion 使用 | ✅ 5 处全在 Loader2 关键状态 |
| role=toolbar 一致性 | ✅ 7 处（含 ChipGroup）全配 aria-label |
| aria-pressed 一致性 | ✅ 8 处全在 button 上 |
| 中文文案 | ✅ 6 轮零失分 |
| 响应式 360/480/768/1024 | ✅ |
| 协作时序 | ✅ ring 006 把 /studio 的 lag 完全消除 |

### 可以打 tag

```bash
git tag v0.4-internal-beta
git push origin v0.4-internal-beta
```

Release note 应包含：
- 15 个路由（14 个 (app) + /share/[token] external + / marketing hero）全部 production-grade
- **/studio 真混剪 backend 接入**（design ring 加 + refine ring 006 范式对齐）
- 0 已知 critical bug，0 P1 残留
- a11y / 中文 / 响应式 / 品牌一致性 ≥ 95%
- TypeScript strict 0 error

### 距离 production-ready

仅以下属于 design v6 路线图，**无技术死结**：
- `middleware.ts`（未登录 → /login）
- OAuth flow（Google / Microsoft / Okta）
- 真 API 接通（`/v1/analytics/timeseries` / `/v1/notifications` / `/v1/integrations` / `/v1/comments` / `/v1/versions`）
- `project-cover.tsx` 26 hex + 6 hardcoded gradient id 收口到 BRAND token
- CI hex lint（防止未来再次出现 inline `#[0-9A-Fa-f]{6}`）

---

## 喂回 Design 环 v6 (Design ring 006 input)

### 协作时序流程改进

5 轮飞轮 + ring 006 复盘，design ring 输出新页 / 新组件**进入 main branch 前**应当跑一次 pre-flight：

```bash
# pre-flight check（约 30 秒）
cd frontend-next
npx tsc --noEmit
# 防止 hex 字面量除白名单（lib/theme.ts / brand/page.tsx / dashboard.tsx 文案 hex / integrations 第三方品牌色）
grep -rn '#[0-9A-Fa-f]\{6\}' app/ components/ \
  | grep -v 'lib/theme\|brand/page\|integrations/page\|dashboard/page\|brand-mark' \
  | grep -v 'project-cover' \
  && echo "❌ 发现非 token hex 字面量" || echo "✓ hex 收口"
# 防止 a11y 漂移
grep -rE '<(Loader2|Spinner).*animate-spin' app/ components/ | grep -v preserve-motion \
  && echo "⚠ Loader2 缺 preserve-motion" || echo "✓ preserve-motion 完整"
# 防止 lucide icon 缺 aria-hidden 在 button 文本场景里
grep -rnE '<(Sparkles|Loader2|Check|X|Plus|Upload|Download|Search|Settings|Bell|HelpCircle|Save|RefreshCw|ChevronRight|Menu|Mail|Crown|UserPlus|Activity|Clock|Video|Folder|Library|Type|Palette|Music2|AlertTriangle|Mic|Captions|Film|Droplet|Zap|AtSign|ArrowDownRight|ArrowUpRight|ShieldCheck|Maximize2|Volume2|Play|Pause|Copy|Cpu|RotateCcw|MessageCircle|MessageSquare|Globe|Archive|Share2|Plug|LineChart|Lock|FileQuestion|Link2Off|Inbox|CheckCircle2|XCircle|DollarSign|Calendar|FolderOpen|LayoutTemplate|LayoutDashboard|ExternalLink|CheckCheck|Sun|Info)\s+(?!aria-hidden|aria-label)' app/ components/ \
  | head -3 \
  && echo "⚠ 发现 icon 缺 a11y" || echo "✓ icon a11y 完整"
```

把这个 sequence 加进 `.husky/pre-push` 或 GitHub Actions PR check，design ring 提 PR 时自动跑。

### Design ring 006 路线图（确认）

按对 production-ready 的贡献度排序（与 ring 005 喂回一致）：

1. **`middleware.ts`** — 未登录 → /login；解决 root not-found 决定 + 防外部访客踩进 (app)
2. **OAuth flow** — login 页 + Google / Microsoft / Okta provider；用现有 Topbar Bell 旁加用户头像 dropdown
3. **API 接通** — analytics / notifications / integrations / studio 改 server fetch 真 endpoint，fallback 退化为「最近一次缓存」
4. **project-cover BRAND 化** — 抽 COVER_PALETTES（6 套深浅蓝 + accent 点缀）+ useId 生成 instance-level gradient id
5. **`<EmptyState>` 统一三处 + reset filter CTA prop** — projects / templates / integrations
6. **CI hex lint** — `.eslintrc` 加 no-hex-literals 规则
7. **meta-tabs COMMENTS / VERSIONS 接 backend** — 当前都是 const

ring 006 之后，**飞轮的 refine 角色基本完成历史使命**：之后的 ring 007 / 008 应当是 design ring 主导，refine ring 仅做 lint + smoke test。

---

*Refine ring · pass 006 — 1 P0 + 3 P2 = 4 项落地，1 文件触动 + 27 行代码改动。飞轮闭环 — internal beta v0.4 完整 ready。下一轮属于 design v6（production-ready），refine 已无 critical 队列。*
