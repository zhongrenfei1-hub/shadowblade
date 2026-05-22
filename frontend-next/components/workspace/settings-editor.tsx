"use client";

import { useState } from "react";
import { Check, Loader2, Save } from "lucide-react";
import {
  type EffectiveSettings,
  type OrganizationSettings,
  type OrganizationSettingsUpdate,
  type UserProfileSettings,
  type UserProfileSettingsUpdate,
  getEffective,
  updateOrganizationSettings,
  updateProfileSettings,
} from "@/lib/api/settings";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface Props {
  organization: OrganizationSettings;
  profile: UserProfileSettings | null;
  effective: EffectiveSettings;
}

type SaveState = "idle" | "saving" | "saved" | "error";

const ASPECTS = ["9:16", "16:9", "1:1", "4:5"] as const;
const CODECS = ["h264", "h265", "vp9"] as const;
const LANGUAGES = ["zh-CN", "en-US", "ja-JP", "ko-KR"];
const TIMEZONES = ["UTC", "Asia/Shanghai", "Asia/Tokyo", "America/New_York", "Europe/Berlin"];

export function SettingsEditor({
  organization: initOrg,
  profile: initProfile,
  effective: initEffective,
}: Props) {
  const [org, setOrg] = useState(initOrg);
  const [profile, setProfile] = useState(initProfile);
  const [effective, setEffective] = useState(initEffective);
  const [orgDraft, setOrgDraft] = useState<OrganizationSettingsUpdate>({});
  const [profileDraft, setProfileDraft] =
    useState<UserProfileSettingsUpdate>({});
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);

  const dirty =
    Object.keys(orgDraft).length > 0 || Object.keys(profileDraft).length > 0;

  function patchOrg<K extends keyof OrganizationSettingsUpdate>(
    key: K,
    value: OrganizationSettingsUpdate[K],
  ) {
    setOrgDraft((d) => ({ ...d, [key]: value }));
    setSaveState("idle");
  }

  function patchProfile<K extends keyof UserProfileSettingsUpdate>(
    key: K,
    value: UserProfileSettingsUpdate[K],
  ) {
    setProfileDraft((d) => ({ ...d, [key]: value }));
    setSaveState("idle");
  }

  function orgVal<K extends keyof OrganizationSettings>(key: K) {
    const v = orgDraft[key as keyof OrganizationSettingsUpdate];
    return v !== undefined ? v : org[key];
  }

  function profileVal<K extends keyof UserProfileSettings>(key: K) {
    const v = profileDraft[key as keyof UserProfileSettingsUpdate];
    if (v !== undefined) return v;
    return profile?.[key];
  }

  async function handleSave() {
    if (!dirty) return;
    setSaveState("saving");
    setError(null);
    try {
      const promises: Promise<unknown>[] = [];
      if (Object.keys(orgDraft).length > 0) {
        promises.push(
          updateOrganizationSettings(orgDraft).then((next) => setOrg(next)),
        );
      }
      if (Object.keys(profileDraft).length > 0) {
        promises.push(
          updateProfileSettings(profileDraft).then((next) => setProfile(next)),
        );
      }
      await Promise.all(promises);
      setOrgDraft({});
      setProfileDraft({});
      // 拉一次 effective 重新反映合并
      const eff = await getEffective();
      setEffective(eff);
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 1500);
    } catch (err) {
      setSaveState("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Effective Settings · 合并后的运行时配置</CardTitle>
            <p className="mt-1 text-[11px] text-muted-foreground">
              三层合并：user profile &gt; organization &gt; defaults
            </p>
          </div>
          <div className="flex items-center gap-3">
            {saveState === "saved" && (
              <Badge variant="done">
                <Check className="h-3 w-3" aria-hidden /> 已保存
              </Badge>
            )}
            {saveState === "error" && <Badge variant="failed">保存失败</Badge>}
            <Button
              onClick={handleSave}
              disabled={!dirty || saveState === "saving"}
            >
              {saveState === "saving" ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Save className="h-4 w-4" aria-hidden />
              )}
              <span>{dirty ? "保存修改" : "无未保存修改"}</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-3 lg:grid-cols-4">
            <KV label="语言" value={effective.language} />
            <KV label="时区" value={effective.timezone} />
            <KV label="画幅" value={effective.aspect_ratio} />
            <KV label="配音" value={effective.voice} />
            <KV label="编码" value={effective.codec} />
            <KV label="LUFS" value={String(effective.loudness_lufs)} />
            <KV
              label="水印"
              value={effective.watermark_enabled ? "开" : "关"}
            />
            <KV label="brand kit" value={String(effective.brand_kit_id)} />
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="p-4 font-mono text-xs text-destructive">
            {error}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>组织默认（影响整个 workspace 的成片）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Selector
              id="org-lang"
              label="语言"
              value={String(orgVal("language"))}
              options={LANGUAGES}
              onChange={(v) => patchOrg("language", v)}
            />
            <Selector
              id="org-tz"
              label="时区"
              value={String(orgVal("timezone"))}
              options={TIMEZONES}
              onChange={(v) => patchOrg("timezone", v)}
            />
            <Selector
              id="org-aspect"
              label="默认画幅"
              value={String(orgVal("default_aspect_ratio"))}
              options={[...ASPECTS]}
              onChange={(v) =>
                patchOrg(
                  "default_aspect_ratio",
                  v as OrganizationSettings["default_aspect_ratio"],
                )
              }
            />
            <Selector
              id="org-codec"
              label="默认编码"
              value={String(orgVal("default_codec"))}
              options={[...CODECS]}
              onChange={(v) =>
                patchOrg(
                  "default_codec",
                  v as OrganizationSettings["default_codec"],
                )
              }
            />
            <div className="grid gap-1">
              <Label htmlFor="org-voice" className="text-xs">默认配音 alias</Label>
              <Input
                id="org-voice"
                value={String(orgVal("default_voice"))}
                onChange={(e) => patchOrg("default_voice", e.target.value)}
              />
            </div>
            <div className="grid gap-1">
              <Label htmlFor="org-lufs" className="text-xs">默认响度 LUFS</Label>
              <Input
                id="org-lufs"
                type="number"
                step="0.5"
                value={Number(orgVal("default_loudness_lufs"))}
                onChange={(e) =>
                  patchOrg("default_loudness_lufs", Number(e.target.value))
                }
              />
            </div>
            <CheckBox
              id="org-watermark"
              label="开启水印"
              checked={Boolean(orgVal("video_watermark_enabled"))}
              onChange={(v) => patchOrg("video_watermark_enabled", v)}
            />
            <CheckBox
              id="org-watermark-draft"
              label="仅草稿打水印"
              checked={Boolean(orgVal("watermark_drafts_only"))}
              onChange={(v) => patchOrg("watermark_drafts_only", v)}
            />
            <CheckBox
              id="org-mfa"
              label="强制 MFA"
              checked={Boolean(orgVal("force_mfa"))}
              onChange={(v) => patchOrg("force_mfa", v)}
            />
            <div className="grid gap-1">
              <Label htmlFor="org-session" className="text-xs">会话时长（小时）</Label>
              <Input
                id="org-session"
                type="number"
                min={1}
                max={168}
                value={Number(orgVal("session_duration_hours"))}
                onChange={(e) =>
                  patchOrg("session_duration_hours", Number(e.target.value))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>个人偏好（只影响当前账号）</CardTitle>
        </CardHeader>
        <CardContent>
          {profile ? (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="grid gap-1">
                <Label htmlFor="profile-nick" className="text-xs">昵称</Label>
                <Input
                  id="profile-nick"
                  value={String(profileVal("nickname") ?? "")}
                  onChange={(e) =>
                    patchProfile("nickname", e.target.value || null)
                  }
                />
              </div>
              <Selector
                id="profile-lang"
                label="界面语言"
                value={String(profileVal("language"))}
                options={LANGUAGES}
                onChange={(v) => patchProfile("language", v)}
              />
              <Selector
                id="profile-tz"
                label="个人时区"
                value={String(profileVal("timezone"))}
                options={TIMEZONES}
                onChange={(v) => patchProfile("timezone", v)}
              />
              <Selector
                id="profile-theme"
                label="主题"
                value={String(profileVal("theme"))}
                options={["system", "light", "dark"]}
                onChange={(v) =>
                  patchProfile(
                    "theme",
                    v as UserProfileSettings["theme"],
                  )
                }
              />
              <Selector
                id="profile-digest"
                label="收件箱摘要"
                value={String(profileVal("inbox_digest"))}
                options={["off", "daily", "weekly"]}
                onChange={(v) =>
                  patchProfile(
                    "inbox_digest",
                    v as UserProfileSettings["inbox_digest"],
                  )
                }
              />
              <CheckBox
                id="profile-email-notif"
                label="邮件通知"
                checked={Boolean(profileVal("email_notifications_enabled"))}
                onChange={(v) =>
                  patchProfile("email_notifications_enabled", v)
                }
              />
              <CheckBox
                id="profile-desktop-notif"
                label="桌面通知"
                checked={Boolean(profileVal("desktop_notifications_enabled"))}
                onChange={(v) =>
                  patchProfile("desktop_notifications_enabled", v)
                }
              />
              <CheckBox
                id="profile-sound"
                label="提示音"
                checked={Boolean(profileVal("sound_enabled"))}
                onChange={(v) => patchProfile("sound_enabled", v)}
              />
              <CheckBox
                id="profile-shortcut"
                label="启用键盘快捷键"
                checked={Boolean(profileVal("keyboard_shortcuts_enabled"))}
                onChange={(v) =>
                  patchProfile("keyboard_shortcuts_enabled", v)
                }
              />
            </div>
          ) : (
            <p className="rounded-md border border-dashed border-border p-4 text-center text-sm text-muted-foreground">
              当前未登录用户，没有个人偏好。
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 rounded-md border border-border bg-card/40 p-3">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <span className="font-mono text-sm">{value}</span>
    </div>
  );
}

function Selector({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid gap-1">
      <Label htmlFor={id} className="text-xs">{label}</Label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-md border border-border bg-background px-2 text-sm"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}

function CheckBox({
  id,
  label,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label
      htmlFor={id}
      className="flex h-9 cursor-pointer items-center gap-2 rounded-md border border-border bg-background px-3 text-sm"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4"
      />
      {label}
    </label>
  );
}
