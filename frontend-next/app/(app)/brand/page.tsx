import { Plus } from "lucide-react";
import { headers } from "next/headers";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { BrandKitEditor } from "@/components/workspace/brand-kit-editor";
import type { BrandKit } from "@/lib/api/brand-kit";

async function loadBrandData(): Promise<{
  active: BrandKit | null;
  list: BrandKit[];
  error: string | null;
}> {
  // server component 直接打 backend — 走绝对地址绕过 next rewrite。
  const base = process.env.BACKEND_URL || "http://localhost:8000";
  const auth = { "X-Workspace-Id": "1", "X-User-Id": "1" } as const;
  // 即使 server 端用 headers() 强制 dynamic，这里只是为了 Next 不要静态化。
  headers();
  try {
    const [activeRes, listRes] = await Promise.all([
      fetch(`${base}/api/v1/brand-kit`, { headers: auth, cache: "no-store" }),
      fetch(`${base}/api/v1/brand-kits`, { headers: auth, cache: "no-store" }),
    ]);
    if (!activeRes.ok)
      throw new Error(`/brand-kit ${activeRes.status}`);
    if (!listRes.ok) throw new Error(`/brand-kits ${listRes.status}`);
    const active: BrandKit = await activeRes.json();
    const list: { items: BrandKit[] } = await listRes.json();
    return { active, list: list.items, error: null };
  } catch (err) {
    return {
      active: null,
      list: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export default async function BrandPage() {
  const { active, list, error } = await loadBrandData();

  if (error || !active) {
    return (
      <section className="grid gap-4">
        <h1 className="font-display text-2xl font-semibold">品牌套件</h1>
        <Card className="border-destructive/40 bg-destructive/5 p-6">
          <h2 className="font-semibold text-destructive">
            无法加载后端 /api/v1/brand-kit
          </h2>
          <p className="mt-2 font-mono text-xs text-destructive/80">
            {error ?? "active kit 为空"}
          </p>
          <p className="mt-3 text-sm text-muted-foreground">
            请确认 backend 已在 :8000 启动（make backend 或 make next）。
          </p>
        </Card>
      </section>
    );
  }

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          品牌套件
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              {active.name}
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              每条成片都对照这套渲染。改一次——所有项目重新渲染。本套件 ID #{active.id}，
              workspace #{active.workspace_id}，作用域 {active.scope}。
            </p>
          </div>
          <div className="flex flex-wrap gap-2 md:gap-3">
            <Button variant="outline">导出 ZIP</Button>
            <Button variant="outline">复制为新版本</Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[260px_1fr] items-start">
        <div className="grid gap-3">
          {list.map((k) => {
            const isActive = k.id === active.id;
            return (
              <Card
                key={k.id}
                className={`cursor-pointer p-3 transition-colors ${
                  isActive ? "border-accent-500/40 bg-accent-500/[0.06]" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    aria-hidden
                    className="h-9 w-9 rounded-md border border-border"
                    style={{
                      background: `linear-gradient(135deg,${k.primary_color},${k.accent_color})`,
                    }}
                  />
                  <div className="leading-tight">
                    <b className="text-sm">{k.name}</b>
                    <span className="block text-[11px] text-muted-foreground">
                      {k.scope} · {k.is_active ? "启用" : "停用"}
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}
          <Button variant="outline">
            <Plus className="h-4 w-4" aria-hidden /> 新建套件
          </Button>
        </div>

        <BrandKitEditor initial={active} />
      </section>
    </>
  );
}
