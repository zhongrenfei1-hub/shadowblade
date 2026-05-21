# ShadowBlade · Next.js 前端

面向企业营销人员的 **AI 视频生成 SaaS**。Next.js 14 App Router + React 18 + Tailwind v3 + shadcn/ui + TypeScript。

## 用户能做到

- **一键填写视频需求** — 模板 + 简报 + 画幅 / 时长 / 配音 / CTA
- **上传企业素材** — 拖拽 / 从素材库选 / AI 自动匹配
- **一键生成完整视频** — 脚本 → 配音 → 字幕 → 混剪 → 封面 → 品牌水印
- **实时预览 + 下载 + 分享** — 内置播放器、MP4 下载、签名分享链接
- **历史记录 + 团队协作** — 项目库、版本对比、评论审批、角色矩阵

## 8 个页面

| 路由 | 用途 |
|---|---|
| `/dashboard` | 工作台 — KPI · 进行中流水线 · 待审批 · 最近项目 |
| `/create` | **核心** — 一键生成向导（模板 / 简报 / 素材 / 大按钮 + 实时进度条）|
| `/projects` | 项目库 — 筛选 + 项目卡片网格 |
| `/projects/[id]` | 详情 — 播放器 + 下载 + 分享链接 + 评论 + 版本 |
| `/library` | 素材库 — 拖拽上传 + 文件夹 + 标签 + 网格 |
| `/templates` | 模板 — 4 列预览 + hover 播放 |
| `/brand` | 品牌套件 — 调色板 + 字体 + 语态 |
| `/team` | 团队 — 成员表 + 角色权限矩阵 |
| `/settings` | 设置 — 通用 / 渲染 / 安全 / API |

## 本地启动

```bash
cd frontend-next
npm install
npm run dev     # 启动在 http://localhost:3001
```

后端如果在跑 `http://localhost:8000`，前端会通过 `next.config.mjs` 的 rewrite 调到 `/api/v1/*`。
后端不在的话，`lib/api.ts` 里有 fallback 数据，UI 照常呈现。

## 设计调性

- 配色：深蓝 `#0F2A4A` · 石墨 `#11161F` · 灰白 `#F7F9FC` · 青绿 `#22D3B7`
- 字体：Inter Display / Inter / JetBrains Mono · 中文回退 PingFang SC / Microsoft YaHei
- 大按钮 / 实时进度 / 拖拽上传 / 状态药丸 / 卡片堆叠

## 技术栈

- **Next.js 14.2** App Router · Server Components 优先
- **Tailwind v3.4** + `tailwindcss-animate` + 自定义 token 调色
- **shadcn/ui 风格** 组件（手写，无 CLI 依赖）：Button / Card / Input / Textarea / Badge / Progress / Avatar / Tabs / Label
- **Radix UI** primitives 做无障碍底层
- **lucide-react** 图标
- **TypeScript 5** strict 模式

## 目录

```
frontend-next/
├ app/
│ ├ layout.tsx              ← root + sidebar + topbar
│ ├ page.tsx                ← redirect to /dashboard
│ ├ globals.css             ← Tailwind base + 设计 token
│ ├ dashboard/page.tsx      ← KPI / 流水线 / 审批 / 项目
│ ├ create/page.tsx         ← 「一键生成」核心
│ ├ projects/
│ │ ├ page.tsx              ← 列表 + 筛选
│ │ └ [id]/page.tsx         ← 播放器 + 下载 + 分享 + 评论
│ ├ library/page.tsx        ← 素材库
│ ├ templates/page.tsx      ← 模板
│ ├ brand/page.tsx          ← 品牌套件
│ ├ team/page.tsx           ← 团队
│ └ settings/page.tsx       ← 设置
├ components/
│ ├ ui/                     ← shadcn 基础组件
│ ├ layout/{sidebar,topbar} ← 应用框架
│ └ workspace/              ← 业务组件
├ lib/
│ ├ api.ts                  ← FastAPI 客户端 + 类型 + fallback
│ └ utils.ts                ← cn / formatBytes / relativeTime
└ public/
```
