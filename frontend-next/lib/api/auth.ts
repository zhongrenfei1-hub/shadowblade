/**
 * Auth API client — /auth/login + /auth/register + /auth/me + /auth/logout.
 *
 * Token 同时存 localStorage（client 端读）和 cookie（Next.js server 端能拿到）。
 * 名字 `sb_token`。这是 demo 级别简单实现；生产用 httpOnly secure cookie。
 */

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  avatar_url: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface AuthOrg {
  id: number;
  slug: string;
  name: string;
  avatar_url: string | null;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
  organizations: AuthOrg[];
  default_workspace_id: number;
  new_organization?: boolean;
}

const IS_SERVER = typeof window === "undefined";
const SERVER_BASE = process.env.BACKEND_URL || "http://localhost:8000";
const BASE = IS_SERVER
  ? `${SERVER_BASE}/api/v1`
  : process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "/api/v1";

const TOKEN_KEY = "sb_token";
const USER_KEY = "sb_user";

export function saveSession(resp: AuthResponse): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, resp.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(resp.user));
  // 同步写 cookie 让 server fetch 也能拿到（demo 用，非 httpOnly）。
  const maxAge = resp.expires_in;
  document.cookie = `${TOKEN_KEY}=${resp.access_token}; path=/; max-age=${maxAge}; samesite=lax`;
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
}

export function getCurrentUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export class AuthApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

async function authRequest<T>(
  path: string,
  body: Record<string, unknown>,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    let msg = `${res.status}`;
    try {
      const parsed = JSON.parse(detail) as { detail?: unknown };
      if (typeof parsed.detail === "string") msg = parsed.detail;
      else if (Array.isArray(parsed.detail)) {
        const first = parsed.detail[0] as { msg?: string } | undefined;
        msg = first?.msg ?? msg;
      }
    } catch {
      msg = detail.slice(0, 200) || msg;
    }
    throw new AuthApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return authRequest<AuthResponse>("/auth/login", { email, password });
}

export function register(
  email: string,
  password: string,
  fullName: string,
): Promise<AuthResponse> {
  return authRequest<AuthResponse>("/auth/register", {
    email,
    password,
    full_name: fullName,
  });
}

export async function logout(): Promise<void> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
  if (token) {
    await fetch(`${BASE}/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    }).catch(() => {
      // 后端 logout 是 stateless，失败也无所谓
    });
  }
  clearSession();
}
