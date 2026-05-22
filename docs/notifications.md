# 工作空间通知（Workspace Notifications）

> 收件箱式事件中心 — 渲染完成 / 品牌偏移 / @ 提及 / 审批 / 计费一处归并，前端 `/(app)/notifications` 顶部 6 个 tab 直接消费。

ShadowBlade 的通知模块借鉴 `fastapi-fullstack-template` 的 *user-inbox* 模式，将其与 React mock 已经稳定下来的 **6 tab + 6 visual kind** 语义对齐。本文档对应代码：

| 层 | 路径 |
|---|---|
| ORM | `backend/app/models/notification.py` |
| Schema | `backend/app/schemas/notification.py` |
| Service | `backend/app/services/notifications.py` |
| API | `backend/app/api/notifications.py` |
| Tests | `backend/tests/notifications/` （63 个用例，全过）|
| 前端 mock 参考 | `frontend-next/app/(app)/notifications/page.tsx` |

---

## 1. 设计目标

- **Workspace-scoped**：每行通知都挂在一个 `workspace_id` 上，权限检查永远不需要 JOIN 用户表 — `WHERE workspace_id = ? AND (user_id = ? OR user_id IS NULL)` 一句话搞定。
- **写时扇出（fan-out-on-write）**：广播事件（模板发布、品牌套件变更）在写入阶段为每个相关用户复制一行。读路径恒等于一次带索引的范围扫描。
- **best-effort**：所有 `notify_*` helper 用 `_swallow` 装饰器吞掉异常 — 通知失败 **绝不能** 把 mix-video / brand-kit 主流程拖垮。
- **enum 单一来源**：`NOTIFICATION_TYPES` / `NOTIFICATION_CATEGORIES` / `NOTIFICATION_KINDS` 三个 tuple 写在 `app/models/notification.py`，Pydantic schema 用 `Literal[...]` 同步约束，API 层 422 自动拦截非法值。
- **可观测**：失败走 `shadowblade.notifications` 日志通道，不噪音化业务日志。

### 与 fastapi-fullstack-template 的对比

| 维度 | fastapi-fullstack-template | ShadowBlade |
|---|---|---|
| 主键作用域 | 单用户（`user_id`） | `workspace_id` + `user_id`（NULL = 广播）|
| 类型层级 | 1 维 `type` | 3 维（type / category / kind）|
| 删除策略 | 软删 | 双轨：`/archive`（soft）与 `DELETE`（hard）|
| 计数端点 | 单 `unread` | `unread` + 分类 `total`|
| 触发方式 | 业务代码直接 INSERT | `notify_*` 高阶 helper（12 个）|
| 失败处理 | 抛错冒泡 | 装饰器吞掉 + 日志 |

---

## 2. 数据模型

### 2.1 表结构 `notifications`

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | INTEGER PK | 自增 |
| `user_id` | INTEGER FK→users（nullable） | NULL = 工作空间广播；非空 = 私人收件 |
| `workspace_id` | INTEGER FK→workspaces | 权限边界 |
| `type` | VARCHAR(48) | 13 个 `NOTIFICATION_TYPES` 之一 |
| `category` | VARCHAR(24) | 6 个 `NOTIFICATION_CATEGORIES` 之一（决定前端 tab）|
| `kind` | VARCHAR(16) | 6 个 `NOTIFICATION_KINDS` 之一（决定图标颜色）|
| `title` | VARCHAR(255) | UI 第一行 |
| `message` | TEXT | UI 第二行 |
| `payload` | JSON | 类型特定的额外字段（task_id / project_id / actor_name ...）|
| `read` | BOOLEAN | 已读标记 |
| `read_at` | DATETIME | 标记已读时间 |
| `archived` | BOOLEAN | 软归档标记，默认列表不显示 |
| `created_at` | DATETIME | 服务器时间 |

### 2.2 索引

| 索引 | 列 | 命中场景 |
|---|---|---|
| `ix_notifications_user_unread_created` | `(user_id, read, created_at)` | header badge 未读计数；用户收件箱默认列表 |
| `ix_notifications_workspace_category_created` | `(workspace_id, category, created_at)` | 按 tab 切换的列表 |
| 单列 `user_id` / `workspace_id` / `type` / `read` / `archived` / `created_at` | — | SQLAlchemy 默认补全 |

### 2.3 三个 enum 的语义

```python
NOTIFICATION_TYPES = (
    "video_generated", "video_failed",
    "template_updated", "template_published",
    "team_invite", "team_member_joined",
    "brand_kit_changed", "brand_drift_detected",
    "mention",
    "approval_requested", "approval_granted",
    "billing", "system",
)
```

`type` 决定 **业务语义**；`category` 决定 **frontend tab 归属**；`kind` 决定 **图标颜色**。

### 2.4 type → category / kind 映射表

| type | category | 默认 kind | 触发位置 |
|---|---|---|---|
| `video_generated` | `pipeline` | `done` | `backend/app/api/mix_video.py:719` |
| `video_failed` | `pipeline` | `fail` | `backend/app/api/mix_video.py:756` |
| `template_updated` | `pipeline` | `info` | 待接入 |
| `template_published` | `pipeline` | `info` | 待接入 |
| `team_invite` | `system` | `info` | 待接入 |
| `team_member_joined` | `system` | `done` | 待接入 |
| `brand_kit_changed` | `drift` | `info` | `backend/app/api/brand_kits.py:236`、`:347` |
| `brand_drift_detected` | `drift` | `warn` | 待接入（混剪阶段 brand-fit 检查）|
| `mention` | `mentions` | `mention` | 待接入（评论组件）|
| `approval_requested` | `approvals` | `info` | 待接入（review queue）|
| `approval_granted` | `approvals` | `done` | 待接入 |
| `billing` | `billing` | `billing` | 待接入（结算 worker）|
| `system` | `system` | `info` | 通用 |

> 映射在 `backend/app/services/notifications.py` 的 `TYPE_CATEGORY` / `TYPE_DEFAULT_KIND` 字典里，所有 helper 共享同一份真值。

---

## 3. API 参考

所有路由前缀 `/api/v1/notifications`。权限通过两个 header 解析：

- `X-Workspace-Id`：缺省回退到 demo workspace（id=1）
- `X-User-Id`：缺省时按 *workspace 广播视图* 检索（owners/admins）

JWT 模式下 `Authorization: Bearer` 优先生效。

### 3.1 `GET /api/v1/notifications`

列出当前调用者可见的通知，按 `created_at DESC, id DESC` 排序。

**查询参数**：

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `limit` | int | 50 | 1–200 |
| `offset` | int | 0 | 翻页偏移 |
| `unread_only` | bool | false | 仅未读 |
| `category` | enum | – | 按 tab 过滤 |
| `type` | enum | – | 精确 type |
| `include_archived` | bool | false | 显示已归档 |

**curl**：

```bash
curl -H "X-Workspace-Id: 1" -H "X-User-Id: 1" \
  "http://localhost:8000/api/v1/notifications?category=pipeline&limit=20"
```

**响应**：

```json
{
  "items": [
    {
      "id": 142,
      "user_id": 1,
      "workspace_id": 1,
      "type": "video_generated",
      "category": "pipeline",
      "kind": "done",
      "title": "视频生成完成 · #901",
      "message": "时长 23.4s · 预设 social-9x16 · 渲染 5.8s",
      "payload": {"task_id": "tsk_8f3a", "project_id": 901, "duration": 23.4},
      "read": false,
      "read_at": null,
      "archived": false,
      "created_at": "2026-05-21T09:00:00"
    }
  ],
  "total": 1,
  "unread": 1,
  "limit": 20,
  "offset": 0
}
```

### 3.2 `GET /api/v1/notifications/unread-count`

```bash
curl -H "X-Workspace-Id: 1" -H "X-User-Id: 1" \
  http://localhost:8000/api/v1/notifications/unread-count
```

```json
{ "unread": 4 }
```

### 3.3 `GET /api/v1/notifications/types`

枚举 frontend 过滤 chip 用的全量类型表。

```json
{
  "types": ["video_generated", "video_failed", "..."],
  "categories": ["pipeline", "approvals", "mentions", "drift", "billing", "system"],
  "kinds": ["done", "mention", "info", "warn", "fail", "billing"],
  "type_to_category": {"video_generated": "pipeline", "...": "..."},
  "type_to_kind": {"video_generated": "done", "...": "..."}
}
```

### 3.4 `GET /api/v1/notifications/{id}`

供邮件 / push 深链跳转，权限校验同 list。404 = 不存在或不属于调用者。

### 3.5 `PUT /api/v1/notifications/{id}/read`

```bash
curl -X PUT -H "X-Workspace-Id: 1" -H "X-User-Id: 1" \
  http://localhost:8000/api/v1/notifications/142/read
```

返回完整 `NotificationRead`。

### 3.6 `PUT /api/v1/notifications/read-all`

可选 `?category=pipeline` 只清单一个 tab。

```json
{ "ok": true, "updated": 12 }
```

### 3.7 `PUT /api/v1/notifications/{id}/archive`

软归档 — 默认列表里消失，但加 `?include_archived=true` 还能查回（审计用）。

### 3.8 `DELETE /api/v1/notifications/{id}`

硬删 — UI 的销毁式 dismiss。

```json
{ "ok": true, "id": 142 }
```

---

## 4. 触发钩点

### 4.1 已接入

| 事件 | 调用位置 | helper |
|---|---|---|
| mix-video 渲染成功 | `backend/app/api/mix_video.py:719` | `notify_video_generated` |
| mix-video 渲染失败 | `backend/app/api/mix_video.py:756` | `notify_video_failed` |
| brand-kit 字段更新 | `backend/app/api/brand_kits.py:236` | `notify_brand_kit_changed` |
| brand-kit logo 上传 | `backend/app/api/brand_kits.py:347` | `notify_brand_kit_changed` |

### 4.2 helper 已就位，等待接入

| 事件 | helper | 建议接入点 |
|---|---|---|
| 模板发布 | `notify_template_published` | `templates` 服务 publish 钩子 |
| 模板更新 | `notify_template_updated` | 模板编辑 PUT 端点 |
| 团队邀请 | `notify_team_invite` | invite 创建 |
| 成员加入 | `notify_team_member_joined` | invite accept |
| 品牌偏移检测 | `notify_brand_drift_detected` | 混剪 brand-fit 阶段 |
| @ 提及 | `notify_mention` | 评论 / 协作组件 |
| 审批请求 | `notify_approval_requested` | review queue 创建 |
| 审批通过 | `notify_approval_granted` | review queue 批准 |
| 计费 | `notify_billing` | 结算 worker / quota 触发器 |

---

## 5. 如何接入新的触发点

只需在业务路径里 `import` helper 并调用。**永远不要**直接写 INSERT — helper 会处理 `category` / `kind` 推导、payload 结构、异常吞噬。

### 5.1 示例：在新的模板 publish 端点里接入

```python
# backend/app/api/templates.py
from app.services import notifications as notifications_svc

@router.post("/templates/publish")
async def publish_template(
    body: TemplatePublishRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: Annotated[int, Depends(get_current_workspace_id)],
    user_id: Annotated[int | None, Depends(get_current_user_id)],
):
    template = await templates_svc.publish(db, body)

    # Inbox event — fire-and-forget；失败不会 502。
    await notifications_svc.notify_template_published(
        workspace_id=workspace_id,
        user_id=user_id,         # None = workspace 广播
        template_name=template.name,
        category=template.scenario,
        db=db,
    )

    return template
```

### 5.2 给整个 workspace 广播

```python
from app.services.notifications import fanout_to_users

await fanout_to_users(
    workspace_id=workspace_id,
    user_ids=[m.user_id for m in members],
    type="template_published",
    title=f"新模板 · {template.name}",
    message="点击试用",
    payload={"template_name": template.name},
    db=db,
)
```

### 5.3 写新 helper 的模板

如果业务需要一个完全新的事件类型：

1. 在 `app/models/notification.py` 的 `NOTIFICATION_TYPES` 加 type 名；
2. 在 `services/notifications.py` 的 `TYPE_CATEGORY` / `TYPE_DEFAULT_KIND` 补映射；
3. 加一个 `@_swallow("notify_xxx")` 修饰的 helper；
4. 在 `tests/notifications/test_triggers.py` 加用例。

---

## 6. 权限模型

### 6.1 隔离机制

每次请求需要解析两个上下文：

- `workspace_id`（必需）— 通过 `get_current_workspace_id` 解析，缺省 fallback 到 `DEMO_WORKSPACE_ID = 1`
- `user_id`（可选）— 通过 `get_current_user_id`，缺省时进入 *workspace 广播视图*

### 6.2 可见性规则

```
SELECT * FROM notifications
WHERE workspace_id = :ws
  AND (user_id = :uid OR user_id IS NULL)
  AND (NOT archived OR :include_archived)
ORDER BY created_at DESC
```

- 用户 A **永远** 看不到工作空间 B 的任何通知
- 用户 A 看得到：(a) 发给自己（`user_id = A.id`）的通知；(b) 工作空间广播（`user_id IS NULL`）
- 用户 A 看不到工作空间 X 里发给用户 B 的通知

### 6.3 失败模式

| 错误 | 状态码 | 原因 |
|---|---|---|
| 不存在的 type/category/kind | 422（Pydantic）或 400（service）| 闭枚举越界 |
| 通知不属于调用者 | 404 | 故意不暴露 403，避免 enum 探测 |
| `workspace_id` 解析失败 | 401 | JWT 模式下没 workspace claim |

---

## 7. 架构图

```
┌────────────────┐
│ Frontend       │   ─── GET /notifications        ───┐
│ /(app)/        │   ─── PUT /{id}/read             ──┤
│ notifications  │   ─── PUT /read-all              ──┤
│  page.tsx      │   ─── DELETE /{id}               ──┤
└────────────────┘                                    │
        ▲                                              ▼
        │                              ┌──────────────────────────┐
        │  NotificationList JSON       │ FastAPI Router           │
        │  {items, total, unread}      │ app/api/notifications.py │
        │                              └──────────────┬───────────┘
        │                                             │
        │                                             ▼
        │                              ┌──────────────────────────┐
        │                              │ Service Layer            │
        │                              │ app/services/            │
        │                              │  notifications.py        │
        │                              │  ├── create_notification │
        │                              │  ├── list_notifications  │
        │                              │  ├── mark_read           │
        │                              │  ├── mark_all_read       │
        │                              │  └── delete_notification │
        │                              └──────────────┬───────────┘
        │                                             │
        │                                             ▼
        │                              ┌──────────────────────────┐
        │                              │ SQLAlchemy ORM           │
        │                              │ app/models/notification  │
        │                              │  (3 复合索引 + workspace  │
        │                              │   隔离 WHERE 子句)        │
        │                              └──────────────┬───────────┘
        │                                             │
        │                                             ▼
        │                              ┌──────────────────────────┐
        │                              │ SQLite / Postgres        │
        │                              │ notifications 表         │
        │                              └──────────────────────────┘
        │                                             ▲
        │                                             │
        │                                             │ INSERT (best-effort,
        │                                             │  @_swallow)
        │                                             │
        │              ┌──────────────────────────────┴───────────┐
        │              │ Trigger Helpers (12 个)                  │
        │              │ services/notifications.py                │
        │              │  ├── notify_video_generated  ←── mix_video.py:719
        │              │  ├── notify_video_failed     ←── mix_video.py:756
        │              │  ├── notify_brand_kit_changed←── brand_kits.py:236, 347
        │              │  ├── notify_template_*       ←── （待接入）
        │              │  ├── notify_mention          ←── （待接入）
        │              │  ├── notify_approval_*       ←── （待接入）
        │              │  └── notify_billing          ←── （待接入）
        │              └──────────────────────────────────────────┘
        │
        └──── 实时刷新：前端用 SWR/react-query 轮询
              unread-count（5–15 秒），列表按需拉取
```

数据流单向：业务路径调 helper → service 写库 → REST 路由按 workspace + user 隔离读出。没有 worker / queue / WebSocket — 一切走 HTTP polling，与 ShadowBlade 其余架构对齐（mix-video 任务状态也用同样的 polling 模式）。

---

## 8. demo seed 数据

跑一次：

```bash
cd backend && .venv/bin/python -m app.services.notifications_demo
```

会清空 demo workspace（id=1）已有的通知行，再注入 12–15 条覆盖全部 6 个 category 的真实示例数据。脚本细节见 `backend/app/services/notifications_demo.py`。

适用场景：

- 本地调通 `/(app)/notifications` 页面后端联调
- 截图 / 录屏前快速重置 demo state
- E2E 测试种子数据
