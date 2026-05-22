# 工作空间通知 · API 参考

ShadowBlade `/api/v1/notifications/*` 接口的完整签名、请求示例、响应示例与错误码。所有端点都按工作空间 + 用户双层 scope 隔离，跨工作空间访问会被自动拒绝。

## 通用约定

### 路径前缀

```
/api/v1/notifications
```

### 必需 HTTP 头

| Header | 类型 | 说明 |
| --- | --- | --- |
| `X-Workspace-Id` | `int` | 工作空间 ID。未传时回退到 demo 工作空间。 |
| `X-User-Id` | `int \| null` | 调用方用户 ID。空时仅能读取广播通知（`user_id IS NULL`）。 |
| `Content-Type` | `application/json` | 仅写操作需要。 |

### 全局错误码

| HTTP | 含义 | 触发条件 |
| --- | --- | --- |
| `200` | OK | 成功 |
| `400` | Bad Request | 枚举值非法（如 `category=xxx`） |
| `404` | Not Found | 通知不存在，或不属于当前 workspace / user |
| `422` | Unprocessable Entity | Pydantic 校验失败（参数缺失、类型不符） |

### 数据模型 · `NotificationRead`

```json
{
  "id": 901,
  "user_id": 12,
  "workspace_id": 1,
  "type": "video_generated",
  "category": "pipeline",
  "kind": "done",
  "title": "Run #901 完成 · 智能腕环",
  "message": "合成 + 渲染共 5 分 38 秒完成。输出 4K，-14 LUFS。",
  "payload": {
    "run_id": 901,
    "project": "wearable-hub",
    "duration_seconds": 338,
    "loudness_lufs": -14
  },
  "read": false,
  "read_at": null,
  "archived": false,
  "created_at": "2026-05-22T08:14:22Z"
}
```

### 封闭枚举

| 字段 | 取值 |
| --- | --- |
| `type` | `video_generated` · `video_failed` · `template_updated` · `template_published` · `team_invite` · `team_member_joined` · `brand_kit_changed` · `brand_drift_detected` · `mention` · `approval_requested` · `approval_granted` · `billing` · `system` |
| `category` | `pipeline` · `approvals` · `mentions` · `drift` · `billing` · `system` |
| `kind` | `done` · `mention` · `info` · `warn` · `fail` · `billing` |

---

## 1 · `GET /api/v1/notifications`

列出收件箱，支持分页与过滤，按 `created_at` 倒序返回。

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `limit` | `int` (1–200) | `50` | 单页条数 |
| `offset` | `int` (≥ 0) | `0` | 偏移量 |
| `unread_only` | `bool` | `false` | 仅返回未读 |
| `category` | `NotificationCategory \| null` | `null` | 按 category 过滤 |
| `type` | `NotificationType \| null` | `null` | 按 type 过滤 |
| `include_archived` | `bool` | `false` | 是否包含已归档项 |

### 请求示例

```bash
curl -X GET 'https://api.shadowblade.cn/api/v1/notifications?limit=20&unread_only=true&category=pipeline' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'
```

### 响应示例

```json
{
  "items": [
    {
      "id": 901,
      "user_id": 12,
      "workspace_id": 1,
      "type": "video_generated",
      "category": "pipeline",
      "kind": "done",
      "title": "Run #901 完成 · 智能腕环",
      "message": "合成 + 渲染共 5 分 38 秒完成。",
      "payload": {"run_id": 901},
      "read": false,
      "read_at": null,
      "archived": false,
      "created_at": "2026-05-22T08:14:22Z"
    }
  ],
  "total": 14,
  "unread": 6,
  "limit": 20,
  "offset": 0
}
```

> `total` 反映当前过滤条件下的总条数；`unread` 始终是该用户在全部 category 上的未读总数（保证 header badge 不被 category tab 误导）。

### 错误码

| HTTP | 触发场景 |
| --- | --- |
| `400` | `category` 或 `type` 不在封闭枚举内 |
| `422` | `limit` 超出 1–200 范围、`offset` < 0 |

---

## 2 · `GET /api/v1/notifications/unread-count`

获取当前用户的未读通知总数。专为 header badge 设计，比走 `GET /` 再读 `unread` 字段轻量。

### 请求示例

```bash
curl -X GET 'https://api.shadowblade.cn/api/v1/notifications/unread-count' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'
```

### 响应示例

```json
{
  "unread": 14
}
```

### 错误码

无业务级错误码，仅可能返回 `500`（数据库异常）。

---

## 3 · `GET /api/v1/notifications/types`

列出 UI filter dropdown 需要的所有封闭枚举与映射关系。比读 OpenAPI schema 便宜，可离线缓存。

### 请求示例

```bash
curl -X GET 'https://api.shadowblade.cn/api/v1/notifications/types' \
  -H 'X-Workspace-Id: 1'
```

### 响应示例

```json
{
  "types": [
    "video_generated", "video_failed", "template_updated",
    "template_published", "team_invite", "team_member_joined",
    "brand_kit_changed", "brand_drift_detected", "mention",
    "approval_requested", "approval_granted", "billing", "system"
  ],
  "categories": [
    "pipeline", "approvals", "mentions", "drift", "billing", "system"
  ],
  "kinds": [
    "done", "mention", "info", "warn", "fail", "billing"
  ],
  "type_to_category": {
    "video_generated": "pipeline",
    "video_failed": "pipeline",
    "approval_requested": "approvals",
    "mention": "mentions",
    "brand_drift_detected": "drift",
    "billing": "billing"
  },
  "type_to_kind": {
    "video_generated": "done",
    "video_failed": "fail",
    "brand_drift_detected": "warn",
    "mention": "mention",
    "billing": "billing"
  }
}
```

### 错误码

无业务级错误码。

---

## 4 · `GET /api/v1/notifications/{id}`

读取单条通知。用于 email / push 通知里的深链跳转。

### 路径参数

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `int` | 通知 ID |

### 请求示例

```bash
curl -X GET 'https://api.shadowblade.cn/api/v1/notifications/901' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'
```

### 响应示例

```json
{
  "id": 901,
  "user_id": 12,
  "workspace_id": 1,
  "type": "video_generated",
  "category": "pipeline",
  "kind": "done",
  "title": "Run #901 完成 · 智能腕环",
  "message": "合成 + 渲染共 5 分 38 秒完成。输出 4K，-14 LUFS。",
  "payload": {"run_id": 901, "project": "wearable-hub"},
  "read": false,
  "read_at": null,
  "archived": false,
  "created_at": "2026-05-22T08:14:22Z"
}
```

### 错误码

| HTTP | 触发场景 |
| --- | --- |
| `404` | 通知不存在 / 跨 workspace / 不属于当前 user |

---

## 5 · `PUT /api/v1/notifications/{id}/read`

将单条通知标记为已读。幂等——重复调用不会重置 `read_at`。

### 请求示例

```bash
curl -X PUT 'https://api.shadowblade.cn/api/v1/notifications/901/read' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'
```

### 响应示例

```json
{
  "id": 901,
  "user_id": 12,
  "workspace_id": 1,
  "type": "video_generated",
  "category": "pipeline",
  "kind": "done",
  "title": "Run #901 完成 · 智能腕环",
  "message": "合成 + 渲染共 5 分 38 秒完成。",
  "payload": {"run_id": 901},
  "read": true,
  "read_at": "2026-05-22T08:21:07Z",
  "archived": false,
  "created_at": "2026-05-22T08:14:22Z"
}
```

### 错误码

| HTTP | 触发场景 |
| --- | --- |
| `404` | 通知不存在 / 不属于当前 workspace + user |

---

## 6 · `PUT /api/v1/notifications/read-all`

批量标记已读。可附 `category` 实现「仅清空当前 tab」。

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `category` | `NotificationCategory \| null` | `null` | 仅清空指定 category，不传则全部清空 |

### 请求示例

```bash
# 全部标记已读
curl -X PUT 'https://api.shadowblade.cn/api/v1/notifications/read-all' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'

# 仅清空「品牌偏移」tab
curl -X PUT 'https://api.shadowblade.cn/api/v1/notifications/read-all?category=drift' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'
```

### 响应示例

```json
{
  "ok": true,
  "updated": 12
}
```

### 错误码

| HTTP | 触发场景 |
| --- | --- |
| `400` | `category` 不在封闭枚举内 |

---

## 7 · `PUT /api/v1/notifications/{id}/archive`

软归档——通知从默认列表中消失，但仍存于数据库（保留审计）。配合 `GET /?include_archived=true` 可查看历史。

### 请求示例

```bash
curl -X PUT 'https://api.shadowblade.cn/api/v1/notifications/889/archive' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'
```

### 响应示例

```json
{
  "id": 889,
  "user_id": 12,
  "workspace_id": 1,
  "type": "mention",
  "category": "mentions",
  "kind": "mention",
  "title": "Marcus Lee 在「Series C 预告」中回复了你",
  "message": "「片尾我同意，标题字号能不能稍微再调小一点。」",
  "payload": {"thread_id": 4421},
  "read": true,
  "read_at": "2026-05-21T22:08:44Z",
  "archived": true,
  "created_at": "2026-05-21T20:01:12Z"
}
```

### 错误码

| HTTP | 触发场景 |
| --- | --- |
| `404` | 通知不存在 / 不属于当前 workspace + user |

---

## 8 · `DELETE /api/v1/notifications/{id}`

硬删除——通知从数据库中移除。UI 上对应「dismiss」按钮的破坏性变体。

### 请求示例

```bash
curl -X DELETE 'https://api.shadowblade.cn/api/v1/notifications/777' \
  -H 'X-Workspace-Id: 1' \
  -H 'X-User-Id: 12'
```

### 响应示例

```json
{
  "ok": true,
  "id": 777
}
```

### 错误码

| HTTP | 触发场景 |
| --- | --- |
| `404` | 通知不存在 / 不属于当前 workspace + user |

---

## 调用顺序示意

```
（页面加载）→ GET /unread-count             → 渲染顶栏徽标
            → GET /                          → 渲染列表
            → GET /types                      → 缓存 dropdown 数据
（点击单条）→ PUT /{id}/read                  → 实时标记已读
（一键清空）→ PUT /read-all?category=...      → 当前 tab 清零
（滑动归档）→ PUT /{id}/archive               → 软归档
（dismiss）→ DELETE /{id}                     → 硬删除
（深链）   → GET /{id}                       → 详情页
```

---

## 速率限制与配额

- **读端点**（`GET *`）：单 token 每分钟 120 次
- **写端点**（`PUT *`, `DELETE *`）：单 token 每分钟 60 次
- 触发限流返回 `429 Too Many Requests`，响应头 `Retry-After` 给出秒数。

## SDK 与生成器

OpenAPI schema 可从 `https://api.shadowblade.cn/openapi.json` 拉取。官方 Python / TypeScript SDK 内联 `NotificationRead` 类型定义；任何后端契约变更都会触发 SDK 重新发版。

---

**版本**：v1 · 与 `backend/app/api/notifications.py` 同步。
**测试覆盖**：63 条单元 + 集成测试全部通过（`backend/tests/api/test_notifications.py`）。
**最后更新**：2026-05-22。
