# i18n batch log — workspace + marketing + auth + drill-downs

44 个剩余页面的中文化记录。所有改动遵循 `docs/i18n-glossary.md` 的术语表与不译清单。每行：文件名 — 关键变更 / 注意事项。

## 通用规则

- 所有文件：`<html lang="en">` → `<html lang="zh-CN">`，`<title>`、`<meta description>`、`<meta og:*>` 全部翻译。
- 可见 UI 文字、表头、按钮、面包屑、aria-label、placeholder、状态徽标、empty-state、表格行、卡片正文全部翻译。
- SVG 内的 `<text>` 标签（含 `STEP 01` / `RENDERING` / `ETA 64s` 等短英文）也翻译。
- JS 数据数组里的展示文本翻译；新增 `STATUS_LABEL` / `KIND_LABEL` / `PRI_LABEL` 等映射表保持 CSS 类名 + 业务 key 英文不变。
- 单位：`min`→`分钟`、`sec`/`s`→`秒`、`min ago`→`分钟前`、`hr ago`→`小时前`、`Yesterday`→`昨天`、`just now`→`刚刚`，`/mo`→`/月`、`/qtr`→`/季度`。
- 不译清单照搬：ShadowBlade、Acme、Helios Logistics、Northwind 等品牌；Okta、Microsoft Entra、Google Workspace、Slack、Notion、Figma、YouTube、LinkedIn、TikTok、Premiere、After Effects、Drive、SharePoint、Salesforce、HubSpot、Looker、Snowflake、PagerDuty、Stripe、SOC 2、ISO 27001、GDPR、HIPAA、SAML、SCIM、OIDC、HMAC、JSON、API、CSV、MP4、H.264、H.265、ProRes、L40S、CDN、SSO、MFA、TLS、cURL、SDK、CLI、RSS、TypeScript、Python、Go、Rust、CRM、SIEM、Splunk、Datadog、SQL、邮箱、URL、变量、`<code>` / `<pre>` 内的代码、CSS 类名、人名。

## 文件清单

- `404.html` — 「片段丢失」+ 工作空间链接组中文化；保留 URL/path 占位符。
- `about.html` — 头部、信念三条、领导团队卡、媒体引述全部翻译；地名（柏林/纽约/东京）汉化。
- `analytics.html` — KPI、图表 X 轴改中文星期、按用途分布、制作人榜单、品牌偏移告警；CSS 类（`sb-pill--running`）保留不变。
- `asset-detail.html` — 元数据表、用法列表、内容嵌入；保留 `sha256:` 哈希值与 `founder-keynote-march.mp4` 文件名。
- `assets.html` — 文件夹/标签筛选、上传引导；JS 数据数组翻译并新增 `KIND_LABEL` 映射。
- `audit-log.html` — 时间、操作者、动作下拉、表格头、6 条事件历史；`verb verb--render` 类名保留。
- `billing.html` — 套餐卡、计量行、支付方式表单、5 张发票全部中文化；保留 INV 编号。
- `brand-kit-compare.html` — 影响预览、v2/v3 两栏对比、3 条「将重新渲染」列表。
- `brand-kit.html` — 色板、字体样本（保留英文「Ship video like product」改为中文示例）、语态该做/避免、Logo 三联。
- `changelog.html` — 头部 + 7 条更新日志（编辑器、品牌套件、L40S、SSO、模板、API、审核体验）。
- `compare.html` — KPI 卡、v16/v17 双面板、4 项变更集；保留 SVG 内英文文案（场景内文字「Your day, on time」是品牌设计示例）。
- `components.html` — 设计系统全部 9 个区块（色彩、字体、圆角、按钮、徽标、进度条、卡片、表格、阶段行、表单、空状态）。
- `customer-story.html` — Helios 客户故事头部 + 3 个指标卡 + 正文 + 引述 + CTA。
- `dev-console.html` — KPI、4 个 Tab、6 条投递记录、payload JSON（保留 JSON 字段名）、5 条 API 密钥。
- `docs.html` — 头部 + 6 个文档分组卡 + curl 示例代码块（注释翻译，载荷字段保留）。
- `features.html` — 6 阶段叙事；保留 SVG 内品牌示例文案，仅翻译标签与中文场景。
- `gallery.html` — 头部统计 + 9 条 REELS 数组中文化。
- `help.html` — Hero + 8 个分类卡 + 5 条 FAQ + 3 张联系卡。
- `integrations.html` — 头部 + 7 个筛选 chip + 15 个集成项名描述（保留品牌名）。
- `job-detail.html` — 4 个 KPI、6 段甘特行、集群活动、日志流（仅翻译时间戳后描述）、3 条审计链。
- `localisation.html` — 源版本面板 + 5 种目标语言卡片，保留各语言的 caption 原文。
- `login.html` — SSO 三按钮 + 邮箱表单 + 右侧 caption。
- `new-video.html` — 4 步向导（模板/简报/品牌/审核）+ 选择项 + 智能建议 + ETA 卡。
- `notifications.html` — 8 个 Tab + 8 条通知行 + 空状态。
- `onboarding.html` — 第 2/4 步「选择起始品牌套件」+ 4 个选项 + SVG 内 Pipeline 标签。
- `press-kit.html` — Logo 4 联、色板 6 块、截图 4 张、6 条事实卡、品牌规范四段。
- `pricing.html` — 计费切换 + 4 个套餐 + 对比表 8 行。
- `project-detail.html` — Hero 元数据、4 个 KPI、6 个版本行（含「v1–v12 折叠」）、表现图。
- `projects.html` — 6 个 chip 筛选 + 表头 + 6 行项目数据（新增 `STATUS_LABEL`）。
- `render-queue.html` — 4 KPI、4 个 worker 卡、5 条队列任务（新增 `PRI_LABEL`）。
- `review.html` — 头部 banner + 播放器 + 决定面板 + 2 条评论 + 签名分享信息。
- `security.html` — Hero + 6 个合规徽章 + 6 个支柱卡 + 合规文档表 7 行。
- `settings.html` — 7 个左导航 + 5 个设置卡片 + 翻转控件 aria-label + cURL 示例代码块。
- `signup.html` — 左侧引述 + 表单 6 字段 + 3 个 SSO 按钮。
- `sitemap.html` — 5 个统计 + 9 个站点分组（覆盖 40 个页面引用）。
- `status.html` — Banner「全部系统正常」+ 6 行服务监控 + 2 条事故复盘。
- `studio.html` — 3 列布局：场景列表（新增 6 条中文 SCENES 数据）+ 简报 + 预览 + 时间线 4 轨 + 详情面板 + 审阅讨论。
- `subscribe.html` — 主题 4 复选框 + 3 个渠道。
- `team.html` — 4 KPI + 6 名成员行（角色徽标）+ 6×5 权限矩阵。
- `templates.html` — 5 个 chip + 8 条 TEMPLATES 数组中文化（badge 「新」/「热门」/「品牌套件」）。
- `template-detail.html` — 预览 + 规格 dl + 5 个场景卡 + 3 个相关模板。
- `upgrade.html` — Hero「25 / 25 已用满」+ 3 个套餐卡（体验版/成长版/规模版）+ 升级按钮。
- `webhook-detail.html` — 4 KPI + 请求 / 响应面板 + 计时拆分 + 2 行尝试历史。
- `webhook-new.html` — 端点配置表单 + 8 个事件复选框 + 测试投递卡 + 示例载荷 + 投递策略 4 行。

## 注意事项

- `workspace-switcher.html` 不在本批 44 个清单内，未触碰（仍是 `lang="en"`）。如需中文化请另开 batch。
- 所有页面保留了 `data-route` / CSS 类名 / JS 变量名 / `href` / SVG 形状 / `<code>` / `<pre>` 内的命令与代码。
- `compare.html` / `studio.html` / `review.html` / `localisation.html` 等含设计示例文案（如「Your day, on time」「without breaking stride」）的页面：上下文表明这是品牌示例英文广告语，保留原文以维持设计真实感。
- `analytics.html` 图表数据星期短标签翻译为中文「周一-周日」；折线图数据值未动。
- `dev-console.html` / `webhook-*` payload JSON 注释翻译，字段名 / 字符串值保留原样以匹配实际 webhook 契约。
