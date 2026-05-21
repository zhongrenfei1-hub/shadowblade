# ShadowBlade

企业级 AI 短视频生成云。一份简报 → 广播级成片，5 分钟内出片，对照你的品牌套件渲染。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI 0.115 · SQLAlchemy 2 异步 · Redis |
| Worker | Celery（渲染、TTS、空镜素材、合成）|
| 前端 | 原生 HTML + 设计令牌（Inter / JetBrains Mono）|
| 存储 | S3 兼容对象存储 |
| 身份 | SAML SSO + SCIM 自动配置 |

## 页面地图（47 页已交付）

> 完整可点击索引：`sitemap.html`。

### 营销侧（公开访问）

| 路由 | 页面 |
| --- | --- |
| `index.html`         | 落地页 — Hero 流水线可视化、客户 logo、特性 |
| `features.html`      | 工作原理 — 脚本 / 分镜 / 配音 / 渲染 四阶段 |
| `pricing.html`       | 4 档计划、年度 / 月度切换、特性对照表 |
| `customer-story.html`| Helios 客户案例 — Hero、KPI、正文、引用、CTA |
| `gallery.html`       | 客户作品集（从 showcase 缩略图加载）|
| `changelog.html`     | 时间轴更新日志 + 分类标签 |
| `docs.html`          | 知识网格 + curl 示例 + Cmd-K 搜索 |
| `security.html`      | 信任徽章 + 6 大支柱 + 合规文档表 |
| `status.html`        | 服务状态页 — 6 个服务、60 分钟节拍条、事故记录 |
| `help.html`          | 帮助中心 — 搜索 + 8 个分类 + FAQ + 联系入口 |
| `about.html`         | 关于我们 — 宣言 + 团队 + 媒体引用 |
| `press-kit.html`     | 媒体资源 — logo、调色板、截图、事实表、品牌规范 |
| `subscribe.html`     | 订阅 — 邮件 + 主题 + RSS / JSON / Slack 渠道 |
| `404.html`           | 片段丢失 — glyph + 路径回显 + 工作台入口 |

### 身份与引导

| 路由 | 页面 |
| --- | --- |
| `login.html`             | SSO 优先（Okta · Entra · Google）+ 邮箱 + 品牌侧栏 |
| `signup.html`            | 分屏 — 营销侧栏 + 60 秒工作空间表单 |
| `onboarding.html`        | 首启引导 — 品牌套件来源选择器 |
| `workspace-switcher.html`| Cmd-K 多租户切换器 |
| `upgrade.html`           | 应用内升级提示 |
| `review.html`            | 外部审核签名链接预览 |

### 工作空间（含侧边栏 shell）

| 路由 | 页面 |
| --- | --- |
| `dashboard.html`       | 工作台 — KPI · 实时流水线 · 待审批 · 项目 |
| `studio.html`          | 编辑器 — 场景导航 + 9:16 画布 + 时间线 + 检视器 + 评审 |
| `projects.html`        | 项目 — 筛选 chips + 密集表格 |
| `project-detail.html`  | 项目详情 — 封面 + 元数据 + KPI + 版本历史 |
| `templates.html`       | 模板库 — 8 张卡片 + 悬停播放 |
| `template-detail.html` | 模板详情 — 预览 + 场景 + 规格 |
| `assets.html`          | 素材库 — 文件夹 + 标签 + 拖拽上传 + 网格 |
| `asset-detail.html`    | 素材详情 — 播放器 + 元数据 + 使用记录 |
| `render-queue.html`    | 渲染队列 — 集群利用率 + 4 个 worker + 优先级 |
| `job-detail.html`      | 流程详情 — Gantt + 实时 GPU 图 + 彩色日志 |
| `compare.html`         | 版本对比 — 双栏 + 变更清单 |
| `localisation.html`    | 本地化 — 5 语言变体网格 |
| `analytics.html`       | 数据分析 — KPI + 7 日柱状 + 排行榜 + 偏移告警 |
| `brand-kit.html`       | 品牌套件 — 切换 + 色板 + 字体 + 语态 + logo |
| `brand-kit-compare.html`| 品牌套件版本对比（v2 ↔ v3）|
| `team.html`            | 团队与权限 — 成员 + 权限矩阵 + SSO |
| `settings.html`        | 设置 — 通用 + 渲染 + 安全 + 计费 + API + 开关 |
| `billing.html`         | 计费与套餐 — 套餐摘要 + 用量计 + 发票 |
| `integrations.html`    | 集成 — 15 张卡片市场（Slack/Notion/Figma/YouTube/…）|
| `dev-console.html`     | 开发者控制台 — Webhook + API 密钥 + 重发 |
| `webhook-detail.html`  | Webhook 投递详情 |
| `webhook-new.html`     | 新建 Webhook |
| `audit-log.html`       | 审计日志 — 防篡改事件流 + 动词色块 |
| `notifications.html`   | 收件箱 — 分类标签 + glyph + 内联操作 |
| `components.html`      | 设计系统 — 全部组件一页 |
| `new-video.html`       | 新建视频向导 — 4 步 + ETA + 智能建议 |
| `sitemap.html`         | 47 页分类链接图 |

## 本地运行

```bash
make install        # 一次性
make dev            # 后端跑 :8000，前端跑 :3000
```

打开 `http://localhost:3000` 看落地页，点「进入工作台」进入主应用。前端会调
`/api/v1/projects`（FastAPI 已开 CORS），后端不在的话自动回退到本地固件数据。

## 四环飞轮

这个仓库由四个并发环构建：

1. **Design 设计环** — 后端 + UI 设计系统 + 所有工作空间页面。10 轮交付（v1 → v10）。
2. **Showcase 展示环** — 品牌素材、营销视觉、产品截图、语态规范、空状态插画。3 轮（45 个 SVG 在 `/showcase/`）。
3. **Test 测试环** — 无障碍、对比度、文案、响应式、品牌一致性审计。4 轮（`docs/test-ring-report-00{1,2,3,4}.md`）。
4. **Refine 精修环** — 应用 Test 发现 + 接入 Showcase 素材。4 轮（数十处修复折叠回 Design 提交）。

产物在 `frontend/`、`backend/`、`showcase/`、`docs/`。整个循环并发运行 — 每环单独提交，2–4 环在每轮 Design 后自动重启。

## 视觉调性

深蓝 `#0F2A4A` + 石墨 `#11161F` + 灰白 `#F7F9FC` + 青绿强调 `#22D3B7`。
Inter Display 用于标题，Inter 用于正文，JetBrains Mono 用于数值与代码。
深色驾驶舱 · 仪表级排版 · 状态药丸是通用词汇表。

完整设计词汇见 `components.html`。

## 中文化

本项目使用简体中文。术语对照表：`docs/i18n-glossary.md`。
品牌名 `ShadowBlade` 保留英文（产品名 / 品牌名）。
所有第三方品牌、技术标准、SDK 名等保留原文。
