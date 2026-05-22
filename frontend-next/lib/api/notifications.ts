/**
 * 通知系统的类型安全 API client。
 *
 * 后端：FastAPI `/api/v1/notifications/*`（8 个端点）。
 * 鉴权：所有请求带 `X-Workspace-Id` + `X-User-Id` header（demo workspace 用 1/1）。
 *
 * URL 解析顺序：
 *   1. `NEXT_PUBLIC_API_BASE_URL`（外部指定的完整 origin，如 https://api.shadowblade.com）
 *   2. `NEXT_PUBLIC_API_BASE`（已有 lib/api.ts 用，通常是 /api/v1 走 next rewrite）
 *   3. fallback `http://localhost:8000/api/v1`（本地直连后端时用）
 *
 * 注意：lib/api.ts 用的相对路径 /api/v1 是默认推荐，因为它走
 * next.config.mjs 的 rewrite，避免 CORS。本文件保持同样约定。
 */

// ─── 类型 ─────────────────────────────────────────────────────────────

export type NotificationType =
  | "video_generated"
  | "video_failed"
  | "template_updated"
  | "template_published"
  | "team_invite"
  | "team_member_joined"
  | "brand_kit_changed"
  | "brand_drift_detected"
  | "mention"
  | "approval_requested"
  | "approval_granted"
  | "billing"
  | "system";

export type NotificationCategory =
  | "pipeline"
  | "approvals"
  | "mentions"
  | "drift"
  | "billing"
  | "system";

export type NotificationKind =
  | "done"
  | "mention"
  | "info"
  | "warn"
  | "fail"
  | "billing";

export interface NotificationRead {
  id: number;
  user_id: number | null;
  workspace_id: number;
  type: NotificationType;
  category: NotificationCategory;
  kind: NotificationKind;
  title: string;
  message: string;
  payload: Record<string, unknown>;
  read: boolean;
  read_at: string | null;
  archived: boolean;
  created_at: string;
}

export interface NotificationList {
  items: NotificationRead[];
  total: number;
  unread: number;
  limit: number;
  offset: number;
}

export interface UnreadCount {
  unread: number;
}

export interface NotificationTypesMeta {
  types: NotificationType[];
  categories: NotificationCategory[];
  kinds: NotificationKind[];
  type_to_category: Record<NotificationType, NotificationCategory>;
  type_to_kind: Record<NotificationType, NotificationKind>;
}

export interface MarkAllReadResult {
  ok: boolean;
  updated: number;
}

export interface DeleteResult {
  ok: boolean;
  id: number;
}

export interface ListParams {
  limit?: number;
  offset?: number;
  unread_only?: boolean;
  category?: NotificationCategory;
  type?: NotificationType;
  include_archived?: boolean;
}

// ─── 内部工具 ─────────────────────────────────────────────────────────

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "/api/v1";

// demo workspace / user — 后续接 SSO 后从 session 取。
const WORKSPACE_ID = "1";
const USER_ID = "1";

function authHeaders(): Record<string, string> {
  return {
    "X-Workspace-Id": WORKSPACE_ID,
    "X-User-Id": USER_ID,
  };
}

function joinUrl(path: string, query?: Record<string, unknown>): string {
  const qs = query
    ? Object.entries(query)
        .filter(([, v]) => v !== undefined && v !== null && v !== "")
        .map(
          ([k, v]) =>
            `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`,
        )
        .join("&")
    : "";
  const sep = qs ? (path.includes("?") ? "&" : "?") : "";
  return `${BASE}${path}${sep}${qs}`;
}

class NotificationsApiError extends Error {
  constructor(
    public status: number,
    public path: string,
    message: string,
  ) {
    super(message);
    this.name = "NotificationsApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { query?: Record<string, unknown> } = {},
): Promise<T> {
  const { query, headers, ...rest } = init;
  const url = joinUrl(path, query);
  const res = await fetch(url, {
    cache: "no-store",
    ...rest,
    headers: {
      ...authHeaders(),
      ...(rest.body ? { "content-type": "application/json" } : {}),
      ...headers,
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new NotificationsApiError(
      res.status,
      path,
      `notifications ${res.status} ${path}: ${detail.slice(0, 300)}`,
    );
  }
  // 204 No Content 不会出现在这里 — 后端目前所有端点都返回 JSON。
  return res.json() as Promise<T>;
}

// ─── 8 个端点 ─────────────────────────────────────────────────────────

/** GET /notifications — 列表 + 分页 + 过滤。 */
export function listNotifications(
  params: ListParams = {},
): Promise<NotificationList> {
  const { limit = 50, offset = 0, ...rest } = params;
  return request<NotificationList>("/notifications", {
    query: { limit, offset, ...rest },
  });
}

/** GET /notifications/unread-count — 当前用户的未读总数。 */
export function getUnreadCount(): Promise<UnreadCount> {
  return request<UnreadCount>("/notifications/unread-count");
}

/** GET /notifications/types — 元数据：所有 type / category / kind 映射。 */
export function getTypes(): Promise<NotificationTypesMeta> {
  return request<NotificationTypesMeta>("/notifications/types");
}

/** GET /notifications/{id} — 单条通知。 */
export function getNotification(id: number): Promise<NotificationRead> {
  return request<NotificationRead>(`/notifications/${id}`);
}

/** PUT /notifications/{id}/read — 标记为已读。 */
export function markRead(id: number): Promise<NotificationRead> {
  return request<NotificationRead>(`/notifications/${id}/read`, {
    method: "PUT",
  });
}

/** PUT /notifications/read-all — 一键全部已读（可按 category 过滤）。 */
export function markAllRead(
  category?: NotificationCategory,
): Promise<MarkAllReadResult> {
  return request<MarkAllReadResult>("/notifications/read-all", {
    method: "PUT",
    query: { category },
  });
}

/** PUT /notifications/{id}/archive — 归档（从列表隐藏，保留可恢复）。 */
export function archive(id: number): Promise<NotificationRead> {
  return request<NotificationRead>(`/notifications/${id}/archive`, {
    method: "PUT",
  });
}

/** DELETE /notifications/{id} — 硬删除。 */
export function deleteNotification(id: number): Promise<DeleteResult> {
  return request<DeleteResult>(`/notifications/${id}`, { method: "DELETE" });
}

export { NotificationsApiError };
