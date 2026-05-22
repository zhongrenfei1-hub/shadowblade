/**
 * Settings API client — 三层（app / organization / profile）+ effective resolver。
 *
 * 后端：`/api/v1/settings` 返回 { profile, organization, effective }，
 *      PUT `/settings/organization` / PUT `/settings/profile` 各自更新一层。
 */

export interface OrganizationSettings {
  display_name: string | null;
  region: string;
  timezone: string;
  language: string;
  default_brand_kit_id: number | null;
  default_template_slug: string | null;
  default_aspect_ratio: "9:16" | "16:9" | "1:1" | "4:5";
  default_voice: string;
  default_codec: "h264" | "h265" | "vp9";
  default_loudness_lufs: number;
  video_watermark_enabled: boolean;
  watermark_drafts_only: boolean;
  auto_render_on_approval: boolean;
  public_preview_links_enabled: boolean;
  sso_provider: string | null;
  force_mfa: boolean;
  session_duration_hours: number;
  ip_allowlist_enabled: boolean;
  ip_allowlist: string[];
  notification_preferences: Record<string, unknown>;
  brand_drift_warning_enabled: boolean;
  allowed_export_formats: string[];
  retention_days: number;
  workspace_id: number;
  created_at: string;
  updated_at: string;
}

export interface UserProfileSettings {
  nickname: string | null;
  avatar_url: string | null;
  bio: string | null;
  language: string;
  timezone: string;
  date_format: "iso" | "us" | "cn";
  theme: "system" | "light" | "dark";
  email_notifications_enabled: boolean;
  desktop_notifications_enabled: boolean;
  mention_notifications_enabled: boolean;
  inbox_digest: "off" | "daily" | "weekly";
  sound_enabled: boolean;
  default_workspace_id: number | null;
  keyboard_shortcuts_enabled: boolean;
  autosave_drafts: boolean;
  user_id: number;
  created_at: string;
  updated_at: string;
}

export interface EffectiveSettings {
  workspace_id: number;
  user_id: number | null;
  brand_kit_id: number | null;
  template_slug: string | null;
  aspect_ratio: string;
  voice: string;
  codec: string;
  loudness_lufs: number;
  watermark_enabled: boolean;
  watermark_drafts_only: boolean;
  language: string;
  timezone: string;
}

export interface SettingsBundle {
  profile: UserProfileSettings | null;
  organization: OrganizationSettings;
  effective: EffectiveSettings;
}

export type OrganizationSettingsUpdate = Partial<
  Omit<OrganizationSettings, "workspace_id" | "created_at" | "updated_at">
>;

export type UserProfileSettingsUpdate = Partial<
  Omit<UserProfileSettings, "user_id" | "created_at" | "updated_at">
>;

const IS_SERVER = typeof window === "undefined";
const SERVER_BASE = process.env.BACKEND_URL || "http://localhost:8000";
const BASE = IS_SERVER
  ? `${SERVER_BASE}/api/v1`
  : process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "/api/v1";

function authHeaders(): Record<string, string> {
  return {
    "X-Workspace-Id": "1",
    "X-User-Id": "1",
  };
}

class SettingsApiError extends Error {
  constructor(
    public status: number,
    public path: string,
    message: string,
  ) {
    super(message);
    this.name = "SettingsApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const { headers, ...rest } = init;
  const res = await fetch(`${BASE}${path}`, {
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
    throw new SettingsApiError(
      res.status,
      path,
      `settings ${res.status} ${path}: ${detail.slice(0, 300)}`,
    );
  }
  return res.json() as Promise<T>;
}

export function getAllSettings(): Promise<SettingsBundle> {
  return request<SettingsBundle>("/settings");
}

export function getEffective(): Promise<EffectiveSettings> {
  return request<EffectiveSettings>("/settings/effective");
}

export function updateOrganizationSettings(
  payload: OrganizationSettingsUpdate,
): Promise<OrganizationSettings> {
  return request<OrganizationSettings>("/settings/organization", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function updateProfileSettings(
  payload: UserProfileSettingsUpdate,
): Promise<UserProfileSettings> {
  return request<UserProfileSettings>("/settings/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export { SettingsApiError };
