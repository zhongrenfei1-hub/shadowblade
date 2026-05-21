# Next.js Showcase 环 · pass 002

> 与 Design 环 commit `80b3326`（流水线术语对齐 6 步标准）+ 后续 `0bf7c88` 的部署调整同步。本轮只新增文件 + 在 `copywriting.ts` 末尾追加常量，未改动任何已交付的 page / shell / ui / workspace / lib。

## 同步基线

| Design 提交 | 影响本轮的内容 |
| --- | --- |
| `80b3326` fix(next): 流水线术语对齐 6 步标准 | 全部 SVG 与文案统一用「脚本 · 分镜 · 配音 · 混剪 · 渲染 · 封面」6 步，不再出现「合成」 |
| `642b59d` fix(next-refine): apply test ring 001 | 文案中的空状态语态与 Test 环 001 报告的发现保持一致 |
| `0bf7c88` chore(next): production build 跳过本地 backend rewrite | `case-studies.ts` 中提到的「分析面板月均值」假设客户工作空间走 production 渲染，与 Vercel 部署路径吻合 |

## 交付清单

### HD 屏 SVG · 5 张

每张为 1600×1000 全屏展示版，逐像素还原 Design 环已交付页的版式语言，去掉真实数据噪音，状态系统读取顺序清晰。`<defs>` 自包含，渐变 id 加文件作用域前缀，无栅格，无远程字体，字体栈用 `Inter Display, Inter, system-ui, sans-serif`。

| 文件 | 大小 | 在产品中的位置 | 用户动作 | 视觉氛围 |
| --- | --- | --- | --- | --- |
| `showcase/screens/screen-press-kit.svg` | 17.0 KB | `press-kit.html` og:image · 媒体发函附图 · 媒体合作页 hero | 一眼看见 logo / 色板 / 截图 / 事实表的"自助下载"形态 | 暗色编辑卡片网格，accent 描边的取色块，资源压缩包按钮 |
| `showcase/screens/screen-billing.svg` | 18.6 KB | `billing.html` og:image · 财务运营 dashboard 配图 · 发票邮件 banner | 看清当前套餐 + 用量 + 发票一栏即可决策续费 | 顶部摘要卡 + 三条用量进度尺 + 发票表，状态徽章按 paid / due / overdue 三色编码 |
| `showcase/screens/screen-dev-console.svg` | 20.4 KB | `dev-console.html` og:image · 开发者文档 hero · 集成市场介绍图 | 找到 Webhook / API Key / 重放三个核心入口 | 三栏面板：左侧 webhook 列表，中间事件流，右侧 API key 管理；JetBrains Mono 注入技术感 |
| `showcase/screens/screen-localisation.svg` | 20.4 KB | `localisation.html` og:image · 国际化产品页 · 客户对外发布配图 | 看到同一支视频在 5 个语种下的变体并排 | 5 列国旗 + 5 行场景缩略图网格，状态环按渲染进度填充 |
| `showcase/screens/screen-about.svg` | 13.7 KB | `about.html` og:image · 企业关于页 · 招聘材料封面 | 在 3 秒内辨认出公司主张 + 领导团队 | 大字主张 + 四个领导监logo + 媒体引述三栏，编辑文学版式 |

### 优化前后对比图 · 2 张

1600×900 横版，左右各占 800×900，中间 1px 分隔，左上角「BEFORE」标签 + 右上角「AFTER」标签，右下角 KPI badge。

| 文件 | 大小 | 主题 | KPI badge | 适用 |
| --- | --- | --- | --- | --- |
| `showcase/compare/before-after-pipeline.svg` | 16.2 KB | 流水线 5 步「合成」→ 6 步「混剪 + 封面」演进 | 「品牌偏移 ↓ 28%」 | 内部周会汇报、产品 changelog、营销「为什么 6 步」段 |
| `showcase/compare/before-after-frontend.svg` | 18.3 KB | 静态 HTML 版前端 → Next.js + shadcn/ui 重构 | 「TTI ↓ 38% · a11y AAA」 | 工程博客、`docs/i18n-glossary.md` 配图、招聘技术栈展示 |

### 文案常量 · 在 `copywriting.ts` 末尾追加

- `ENTERPRISE_LANDING` · 企业版落地页 6 个 section（hero / trust / pipeline / governance / roi / cta）
- `INDUSTRY_USE_CASES` · 4 个行业用例（电商 / 金融 / 培训 / 政企）
- `OBJECTION_HANDLING` · 6 条常见异议+回应
- 配套 TypeScript 接口与 key union 类型导出，与现有 `EmptyStateKey` 风格一致

### 长形态案例 · 新文件

- `frontend-next/components/marketing/case-studies.ts` · 3 个叙事案例
  - `helios-wearable-hub-spring-launch` · Helios · 消费硬件
  - `wearable-hub-localisation-engine` · Wearable Hub · 本地化运营
  - `se-bootcamp-onboarding-academy` · SE Bootcamp · 企业培训
- 接口 `CaseStudy` + `CaseStudyQuote`，常量后置 `as const satisfies readonly CaseStudy[]`，slug 列表导出 `CaseStudySlug` 字面量联合类型

## 给 Test 环的提示

- 5 张新 HD 屏 SVG 需要 a11y 检查：每张里关键文字色对比度是否 ≥ 4.5（特别是 `screen-billing.svg` 的 due / overdue 状态徽章）
- `ENTERPRISE_LANDING.trust.bullets` 含「SOC2 · Type II」「ISO 27001」「GDPR · HIPAA · DPA 模板」「数据驻留 · EU · US · APAC」「审计日志保留 7 年」—— 若市场或法务对外口径有出入，请回报
- `case-studies.ts` 的引述 quote.text 都是虚拟客户，若进入真实客户阶段需要走审签流程

## 给 Refine 环的提示

- 如果调整 `accent #22D3B7` 或 `secondary #38BDF8`，全部 7 个新 SVG 文件中的渐变 stop 需要回归（搜索 `stop-color="#22D3B7"` / `stop-color="#38BDF8"`）
- 如果流水线步骤名再次调整（例如「封面」→「缩略图」），需要回归：
  - `showcase/compare/before-after-pipeline.svg` 右侧 6 个步骤卡的文字
  - `ENTERPRISE_LANDING.pipeline.bullets` 6 条列表
  - `case-studies.ts` 中 approach 字段的描述
- 禁用词清单（赋能 / 抓手 / 闭环 / 链路 / 打通 / 一站式 / 极致 / 无缝 / 全方位 / 重磅）和「不用感叹号 / 不用您」规则已嵌进 `copywriting.ts` 文件头注释，未来追加文案直接参照

## 取舍备注

1. `screen-localisation.svg` 用了 5 国旗 emoji-like SVG 表达，没有走真实国旗几何（合规与简化的平衡）；如果需要更严肃可换成 ISO 语言代码徽章
2. `before-after-frontend.svg` 左侧的静态 HTML 版做了"略简陋"的视觉化处理（统一灰阶 + 较松排版），并非否定旧版本，而是强调对比；如果用于对外宣传需要润色文案搭配
3. `ENTERPRISE_LANDING.roi` 的三条数字（4 分钟出片 / 68% 提速 / $184k 节省）与 `case-studies.ts` 内的 Helios 案例数字保持一致，方便落地页内交叉引用；改动时记得同时更新两处

## 不在本轮范围

- 视频版 demo（HyperFrames / 动画） · 拟在 pass 003 评估
- 企业 RFP 模板 / 一页纸 PDF · 等市场反馈再启动
- 真实客户照片或 logo 授权 · 待法务流程
