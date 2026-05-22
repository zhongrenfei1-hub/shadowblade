"use client";

import { useState } from "react";
import { Check, Loader2, Save } from "lucide-react";
import {
  type BrandKit,
  type BrandKitUpdate,
  updateActiveKit,
} from "@/lib/api/brand-kit";
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

type FieldKey =
  | "primary_color"
  | "secondary_color"
  | "accent_color"
  | "neutral_color"
  | "background_color";

const SWATCHES: { key: FieldKey; label: string }[] = [
  { key: "primary_color", label: "主色" },
  { key: "accent_color", label: "强调" },
  { key: "secondary_color", label: "辅色" },
  { key: "neutral_color", label: "中性" },
  { key: "background_color", label: "背景" },
];

type SaveState = "idle" | "saving" | "saved" | "error";

export function BrandKitEditor({ initial }: { initial: BrandKit }) {
  const [kit, setKit] = useState<BrandKit>(initial);
  const [draft, setDraft] = useState<BrandKitUpdate>({});
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const dirty = Object.keys(draft).length > 0;

  function patch<K extends keyof BrandKitUpdate>(
    key: K,
    value: BrandKitUpdate[K],
  ) {
    setDraft((d) => ({ ...d, [key]: value }));
    setSaveState("idle");
  }

  async function handleSave() {
    if (!dirty) return;
    setSaveState("saving");
    setErrorMsg(null);
    try {
      const next = await updateActiveKit(draft);
      setKit(next);
      setDraft({});
      setSaveState("saved");
      setTimeout(() => setSaveState("idle"), 1500);
    } catch (err) {
      setSaveState("error");
      setErrorMsg(err instanceof Error ? err.message : String(err));
    }
  }

  function valueOf<K extends keyof BrandKitUpdate>(key: K): string {
    const v = draft[key] ?? (kit[key as keyof BrandKit] as unknown);
    return typeof v === "string" ? v : (v ?? "").toString();
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div className="grid gap-1">
            <CardTitle>{kit.name}</CardTitle>
            <span className="text-[11px] text-muted-foreground">
              workspace #{kit.workspace_id} · scope {kit.scope} · 上次更新{" "}
              {new Date(kit.updated_at).toLocaleString("zh-CN")}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {saveState === "saved" && (
              <Badge variant="done">
                <Check className="h-3 w-3" aria-hidden /> 已保存
              </Badge>
            )}
            {saveState === "error" && (
              <Badge variant="failed">保存失败</Badge>
            )}
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
        {errorMsg && (
          <CardContent>
            <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 font-mono text-xs text-destructive">
              {errorMsg}
            </p>
          </CardContent>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>调色板 — 编辑后点保存推送到 /api/v1/brand-kit</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            {SWATCHES.map(({ key, label }) => {
              const v = valueOf(key);
              return (
                <div key={key} className="grid gap-2">
                  <Label htmlFor={`brand-${key}`} className="text-xs">
                    {label}
                  </Label>
                  <div
                    className="grid h-16 place-items-center rounded-md border border-border font-mono text-xs"
                    style={{
                      background: v,
                      color: ["#FFFFFF", "#F7F9FC", "#F5F7FB"].includes(
                        v.toUpperCase(),
                      )
                        ? "#0F2A4A"
                        : "#F7F9FC",
                    }}
                  >
                    {v}
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      id={`brand-${key}`}
                      type="color"
                      value={v}
                      onChange={(e) => patch(key, e.target.value.toUpperCase())}
                      className="h-9 w-12 cursor-pointer rounded border border-border bg-transparent"
                      aria-label={`${label}颜色选择器`}
                    />
                    <Input
                      value={v}
                      onChange={(e) =>
                        patch(key, e.target.value.toUpperCase())
                      }
                      className="font-mono text-xs"
                      maxLength={9}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>字体 & 水印 & 字幕</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="grid gap-2">
              <Label htmlFor="brand-name" className="text-xs">套件名</Label>
              <Input
                id="brand-name"
                value={valueOf("name")}
                onChange={(e) => patch("name", e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="brand-font" className="text-xs">主字体</Label>
              <Input
                id="brand-font"
                value={valueOf("font_family")}
                onChange={(e) => patch("font_family", e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="brand-watermark" className="text-xs">水印文字</Label>
              <Input
                id="brand-watermark"
                value={valueOf("watermark_text")}
                placeholder="留空则不显示文字水印"
                onChange={(e) =>
                  patch("watermark_text", e.target.value || null)
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="brand-watermark-pos" className="text-xs">
                水印位置 (tl/tr/bl/br/bc)
              </Label>
              <Input
                id="brand-watermark-pos"
                value={valueOf("watermark_position")}
                onChange={(e) =>
                  patch(
                    "watermark_position",
                    e.target.value as BrandKitUpdate["watermark_position"],
                  )
                }
                maxLength={2}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="brand-lufs" className="text-xs">
                响度目标 LUFS（社交平台标准 -14）
              </Label>
              <Input
                id="brand-lufs"
                type="number"
                step="0.5"
                value={valueOf("target_lufs")}
                onChange={(e) =>
                  patch("target_lufs", Number(e.target.value))
                }
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="brand-sub-size" className="text-xs">字幕字号</Label>
              <Input
                id="brand-sub-size"
                type="number"
                value={valueOf("subtitle_size")}
                onChange={(e) =>
                  patch("subtitle_size", Number(e.target.value))
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
