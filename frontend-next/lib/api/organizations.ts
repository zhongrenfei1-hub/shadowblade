/**
 * Organizations / Teams API client。
 *
 * 这里的端点都要求 JWT，所以本模块自带"demo 登录"流程：第一次调用时
 * 用 demo@example.com / demo1234 自动 register-or-login，把 access_token
 * 缓存到模块级变量，后续请求带 Authorization: Bearer。
 *
 * 生产环境会被真正的 SSO + cookie session 替换。
 */

// Backend canonical roles (see app/core/permissions.py). `editor`/`viewer`
// are kept as legacy aliases on the backend for cross-version safety but
// new code should emit `member`/`guest`.
export type Role = "owner" | "admin" | "member" | "guest";

export interface Organization {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  owner_id: number;
  plan: string;
  seats: number;
  monthly_render_quota: number;
  monthly_render_used: number;
  created_at: string;
  updated_at: string;
  role: Role;
  member_count: number;
}

export interface Member {
  id: number;
  workspace_id: number;
  user_id: number;
  role: Role;
  invited_by: number | null;
  joined_at: string;
  user: {
    id: number;
    full_name: string;
    avatar_url: string | null;
  };
}

export interface Invitation {
  id: number;
  workspace_id: number;
  email: string;
  role: Role;
  /**
   * Secret URL-safe token (32 chars) the invitee uses to claim the seat.
   *
   * IMPORTANT: this is the backend field name. The earlier version of
   * the client typed it as ``code`` and never received a value because
   * the backend returns ``invite_code``. Renaming here unblocks the
   * "copy invite link" UI flow.
   */
  invite_code: string;
  status: "pending" | "accepted" | "revoked" | "expired";
  invited_by: number | null;
  inviter?: {
    id: number;
    full_name: string;
    avatar_url: string | null;
  } | null;
  expires_at: string;
  accepted_at: string | null;
  accepted_by: number | null;
  created_at: string;
}

export interface InvitationPublic {
  invite_code: string;
  workspace_id: number;
  workspace_name: string | null;
  role: Role;
  status: "pending" | "accepted" | "revoked" | "expired";
  expires_at: string;
  email: string;
}

export interface InvitationAcceptResponse {
  membership_id: number;
  workspace_id: number;
  role: Role;
  accepted_at: string;
}

const IS_SERVER = typeof window === "undefined";
const SERVER_BASE = process.env.BACKEND_URL || "http://localhost:8000";
const BASE = IS_SERVER
  ? `${SERVER_BASE}/api/v1`
  : process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "/api/v1";

const DEMO_EMAIL = "demo@example.com";
const DEMO_PASSWORD = "demo1234";
const DEMO_NAME = "Demo User";

let cachedToken: string | null = null;
let inflightLogin: Promise<string> | null = null;

async function loginOrRegister(): Promise<string> {
  // 先尝试 login（用户已存在时走这条路）
  let res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: DEMO_EMAIL, password: DEMO_PASSWORD }),
    cache: "no-store",
  });
  // 失败则尝试注册（首次启动 / 数据库重建）
  if (!res.ok) {
    res = await fetch(`${BASE}/auth/register`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: DEMO_EMAIL,
        password: DEMO_PASSWORD,
        full_name: DEMO_NAME,
      }),
      cache: "no-store",
    });
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`auth bootstrap failed ${res.status}: ${detail.slice(0, 200)}`);
  }
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
}

async function ensureToken(): Promise<string> {
  if (cachedToken) return cachedToken;
  if (!inflightLogin) {
    inflightLogin = loginOrRegister().finally(() => {
      inflightLogin = null;
    });
  }
  const t = await inflightLogin;
  cachedToken = t;
  return t;
}

class OrganizationsApiError extends Error {
  constructor(
    public status: number,
    public path: string,
    message: string,
  ) {
    super(message);
    this.name = "OrganizationsApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = await ensureToken();
  const { headers, ...rest } = init;
  let res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    ...rest,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(rest.body ? { "content-type": "application/json" } : {}),
      ...headers,
    },
  });
  // 缓存的 token 失效时（401），强制刷新一次重试。
  if (res.status === 401 && cachedToken) {
    cachedToken = null;
    const newToken = await ensureToken();
    res = await fetch(`${BASE}${path}`, {
      cache: "no-store",
      ...rest,
      headers: {
        Authorization: `Bearer ${newToken}`,
        ...(rest.body ? { "content-type": "application/json" } : {}),
        ...headers,
      },
    });
  }
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new OrganizationsApiError(
      res.status,
      path,
      `organizations ${res.status} ${path}: ${detail.slice(0, 300)}`,
    );
  }
  // DELETE 可能返回 204
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── Organizations ────────────────────────────────────────────────────

export function listOrganizations(): Promise<Organization[]> {
  return request<Organization[]>("/organizations");
}

export function getOrganization(id: number): Promise<Organization> {
  return request<Organization>(`/organizations/${id}`);
}

// ─── Members ──────────────────────────────────────────────────────────

export function listMembers(orgId: number): Promise<Member[]> {
  return request<Member[]>(`/organizations/${orgId}/members`);
}

export function updateMemberRole(
  orgId: number,
  userId: number,
  role: Role,
): Promise<Member> {
  return request<Member>(`/organizations/${orgId}/members/${userId}`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

export function removeMember(
  orgId: number,
  userId: number,
): Promise<{ ok: boolean } | void> {
  return request<{ ok: boolean }>(
    `/organizations/${orgId}/members/${userId}`,
    { method: "DELETE" },
  );
}

// ─── Invitations ──────────────────────────────────────────────────────

export function listInvitations(orgId: number): Promise<Invitation[]> {
  return request<Invitation[]>(`/organizations/${orgId}/invitations`);
}

export function inviteMember(
  orgId: number,
  email: string,
  role: Role,
): Promise<Invitation> {
  return request<Invitation>(`/organizations/${orgId}/invitations`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });
}

export function revokeInvitation(
  orgId: number,
  inviteId: number,
): Promise<{ ok: boolean } | void> {
  return request<{ ok: boolean }>(
    `/organizations/${orgId}/invitations/${inviteId}`,
    { method: "DELETE" },
  );
}

// ─── Public invitation endpoints (no membership required) ─────────────

/**
 * Inspect an invitation by its public code. Used by the
 * ``/invite/[code]`` landing page to render "you've been invited to X"
 * before the user logs in.
 *
 * Bypasses :func:`ensureToken` because the endpoint is intentionally
 * unauthenticated; a JWT is only needed when the user clicks "accept".
 */
export async function inspectInvitation(
  code: string,
): Promise<InvitationPublic> {
  const res = await fetch(`${BASE}/invitations/${encodeURIComponent(code)}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new OrganizationsApiError(
      res.status,
      `/invitations/${code}`,
      `invite lookup ${res.status}: ${detail.slice(0, 200)}`,
    );
  }
  return res.json();
}

/**
 * Accept an invitation. Requires the calling user's JWT to match the
 * invitation's addressee email (case-insensitive). Returns the freshly
 * minted membership row so the caller can navigate straight to the
 * org dashboard.
 */
export function acceptInvitation(
  code: string,
): Promise<InvitationAcceptResponse> {
  return request<InvitationAcceptResponse>(
    `/invitations/${encodeURIComponent(code)}/accept`,
    { method: "POST" },
  );
}

// ─── Auth / current-user helpers ──────────────────────────────────────

export interface AuthMe {
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    avatar_url: string | null;
  };
  organizations: Array<{
    id: number;
    slug: string;
    name: string;
    role: Role;
  }>;
  default_workspace_id: number | null;
}

/**
 * Return the currently authenticated user + org memberships.
 *
 * Used by the TeamEditor's "is this me?" check — the previous
 * implementation compared against ``org.owner_id``, which conflated
 * "owner of the org" with "the caller", and locked the wrong row.
 */
export function authMe(): Promise<AuthMe> {
  return request<AuthMe>("/auth/me");
}

export { OrganizationsApiError };
