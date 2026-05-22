import { headers } from "next/headers";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SettingsEditor } from "@/components/workspace/settings-editor";
import { getAllSettings } from "@/lib/api/settings";

async function loadSettings() {
  headers();
  try {
    const bundle = await getAllSettings();
    return { bundle, error: null };
  } catch (err) {
    return {
      bundle: null,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export default async function SettingsPage() {
  const { bundle, error } = await loadSettings();

  if (error || !bundle) {
    return (
      <section className="grid gap-4">
        <h1 className="font-display text-2xl font-semibold">设置</h1>
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">无法加载设置</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-xs text-destructive">{error}</p>
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          设置
        </span>
        <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
          App / Org / User 三层设置
        </h1>
        <p className="max-w-prose text-sm text-muted-foreground">
          组织默认影响整个 workspace 的成片；个人偏好只影响当前账号。
          顶部「Effective」卡片实时反映三层合并后最终生效的值。
        </p>
      </section>

      <SettingsEditor
        organization={bundle.organization}
        profile={bundle.profile}
        effective={bundle.effective}
      />
    </>
  );
}
