# Showcase · 工作空间通知

ShadowBlade 工作空间通知（Notifications）功能的对外展示页面。整套 showcase 静态化、零外部依赖（除 Google Fonts 提供 Inter / JetBrains Mono），用浏览器直接打开 `index.html` 即可演示。

## 目录用途

| 文件 | 用途 | 用法 |
| --- | --- | --- |
| `index.html` | 主展示页 · 收件箱 UI + 六种 kind + 空状态 + API 索引 | 浏览器直接打开；或作为产品页 iframe 嵌入 |
| `notification-states.svg` | 六种通知 kind 视觉对照（300×600） | 销售一页材料、文档侧栏插图、`og:image` |
| `api-reference.md` | 完整 API 参考（5 端点 + 2 便利端点） | 后端联调、SDK 作者、客户的 IT 团队 |

## 设计原则

承接 `showcase/` 既有规范（见 `../INDEX.md` Pass 001–003 与 `../brand/voice-and-tone.md`）：

1. **暗色驾驶舱**——延续 dashboard / studio / queue 三屏的 navy-950 → graphite-900 渐变，配 `#22D3B7` 主重点色 + `#38BDF8` 次重点色。
2. **每种 kind = 一种语义 = 一种色**——六种通知 kind 与 tokens 中的 `--sb-status-*` 一一对应：

   | Kind | 中文 | 色值 | 语义场景 |
   | --- | --- | --- | --- |
   | `done` | 完成 | `#22D3B7` | 渲染完成、审批通过、模板发布 |
   | `mention` | @ 提及 | `#A78BFA` | 评论点名、审批指派 |
   | `info` | 状态变更 | `#38BDF8` | 流水线启动、worker 上线 |
   | `warn` | 品牌偏移 | `#FBBF24` | 配色越界、字体替换、可一键修 |
   | `fail` | 失败 | `#F87171` | 渲染失败、配音错配 |
   | `billing` | 计费 | `#D8DDE5` | 用量检查点、超额预警、对账 |

3. **三种条目状态**：
   - **未读**：左缘绿色 dot + 背景 4% 绿色高亮 + 标题用 `--sb-text`
   - **已读**：背景透明 + 标题降为 `--sb-text-muted` + glyph opacity 0.55
   - **归档**：右移 8px + 整体 opacity 0.46 + 紫色「已归档」徽章
4. **企业级文案 tone**——平静、声明式、不夸张、单位齐全。沿用 `brand/voice-and-tone.md` 的「Outcome-first / Specific over clever / Quiet authority」三原则。
5. **完全自包含**——`index.html` 内联 CSS、内联 SVG，不依赖 `tokens.css` / `app.css`，便于在销售环境、客户演示机、离线 demo 中使用。

## 文案与示例数据

页面中的四条主示例覆盖了实际生产中最高频的事件类型：

| # | 类型 | Kind | 解决的对话场景 |
| --- | --- | --- | --- |
| 1 | `video_generated` | done | 「我的 901 跑完了吗？」 |
| 2 | `mention` | mention | 「Priya 在评论里 @ 我说要看片尾」 |
| 3 | `brand_drift_detected` | warn | 「这两条配色不对，要不要换」 |
| 4 | `video_failed` + `billing` | fail / billing | 「为什么这条卡住了？这季度还能跑多少？」 |

## 如何嵌入到产品页

```html
<!-- 在 notifications.html 顶部加入对应 og:image -->
<meta property="og:image" content="/showcase/notifications/notification-states.svg" />

<!-- 在 features.html / changelog.html 引用截图 -->
<img src="/showcase/notifications/index.html"
     alt="ShadowBlade 工作空间收件箱预览"
     loading="lazy" />
```

如需作为 iframe 嵌入（避免样式串扰），不需要任何额外配置；`index.html` 已隔离自己的 CSS 命名空间。

## 与后端的对照关系

页面里展示的所有字段、kind、category 都与 `backend/app/models/notification.py` 中的封闭枚举严格对齐。
完整 API（5 个核心端点 + 2 个便利端点）的请求 / 响应签名见同目录 `api-reference.md`。

如需修改可视化设计：

- 颜色：编辑 `index.html` 顶部 `:root` 块中的 `--sb-status-*` 变量
- 字体：默认通过 Google Fonts 加载 Inter + JetBrains Mono；如需离线，可改为本地 woff2
- 示例条目：直接编辑 `.inbox-list` 区块中的 `.notify` 元素

## 来源与版本

- 后端实现：`backend/app/{api,services,schemas,models}/notification.py`
- 测试：63 条单元 + 集成测试全部通过
- 设计参考：`frontend/public/notifications.html`（产品内页面）
- Showcase 风格守护：`showcase/INDEX.md` Pass 003 之后的整体规范

**初始版本** · Pass 004 · 2026-05-22 · 与后端 v1 端点同步发布。
