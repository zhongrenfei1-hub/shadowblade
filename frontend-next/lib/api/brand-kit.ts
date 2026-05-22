/**
 * 品牌套件 API client — 仿 lib/api/notifications.ts 的范本。
 *
 * 后端：FastAPI `/api/v1/brand-kit` (单数 active kit) + `/api/v1/brand-kits` (复数列表)。
 * 鉴权：demo workspace 走 X-Workspace-Id=1 / X-User-Id=1 header；
 *       生产对接 JWT 后从 session 取。
 */

export interface BrandKit {
  id: number;
  workspace_id: number;
  scope: "workspace" | "user";
  owner_id: number | null;
  is_active: boolean;
  name: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  neutral_color: string;
  background_color: string;
  font_family: string;
  font_heading: string;
  font_body: string;
  logo_url: string | null;
  logo_mono_url: string | null;
  intro_url: string | null;
  outro_url: string | null;
  watermark_text: string | null;
  watermark_opacity: number;
  watermark_position: "tl" | "tr" | "bl" | "br" | "bc";
  watermark_width_pct: number;
  voice: string;
  target_lufs: number;
  target_tp: number;
  bgm_gain_db: number;
  subtitle_size: number;
  subtitle_margin_v: number;
  default_template_name: string | null;
  custom_css_snippet: string | null;
  tone: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type BrandKitUpdate = Partial<
  Pick<
    BrandKit,
    | "name"
    | "primary_color"
    | "secondary_color"
    | "accent_color"
    | "neutral_color"
    | "background_color"
    | "font_family"
    | "font_heading"
    | "font_body"
    | "watermark_text"
    | "watermark_opacity"
    | "watermark_position"
    | "watermark_width_pct"
    | "voice"
    | "target_lufs"
    | "subtitle_size"
    | "subtitle_margin_v"
  >
>;

export interface BrandKitLogoResponse {
  logo_url: string;
  width: number;
  height: number;
  bytes: number;
}

const BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE ||
  "/api/v1";

const WORKSPACE_ID = "1";
const USER_ID = "1";

function authHeaders(): Record<string, string> {
  return {
    "X-Workspace-Id": WORKSPACE_ID,
    "X-User-Id": USER_ID,
  };
}

class BrandKitApiError extends Error {
  constructor(
    public status: number,
    public path: string,
    message: string,
  ) {
    super(message);
    this.name = "BrandKitApiError";
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
      ...(rest.body && !(rest.body instanceof FormData)
        ? { "content-type": "application/json" }
        : {}),
      ...headers,
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new BrandKitApiError(
      res.status,
      path,
      `brand-kit ${res.status} ${path}: ${detail.slice(0, 300)}`,
    );
  }
  return res.json() as Promise<T>;
}

/** GET /brand-kit — 当前 workspace/user 解析后的 active kit。 */
export function getActiveKit(): Promise<BrandKit> {
  return request<BrandKit>("/brand-kit");
}

/** GET /brand-kits — workspace 下所有 kit 的列表。 */
export function listKits(): Promise<{ items: BrandKit[] }> {
  return request<{ items: BrandKit[] }>("/brand-kits");
}

/** PUT /brand-kit — PATCH 风格的更新，只送修改字段。 */
export function updateActiveKit(payload: BrandKitUpdate): Promise<BrandKit> {
  return request<BrandKit>("/brand-kit", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/** POST /brand-kit/logo — 上传 logo (multipart)。 */
export function uploadLogo(file: File): Promise<BrandKitLogoResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<BrandKitLogoResponse>("/brand-kit/logo", {
    method: "POST",
    body: form,
  });
}

export { BrandKitApiError };
