import { Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SettingsForm } from "@/components/workspace/settings-form";

const SECTIONS = [
  { id: "general", label: "通用" },
  { id: "render", label: "渲染与画质" },
  { id: "security", label: "安全与 SSO" },
  { id: "billing", label: "套餐与计费" },
  { id: "integrations", label: "集成" },
  { id: "api", label: "API 与 Webhook" },
];

export default function SettingsPage() {
  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">工作空间设置</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">设置</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              流水线、安全、计费、集成。改动作用于整个工作空间，并写入审计日志。
            </p>
          </div>
          <div className="flex gap-2 md:gap-3">
            <Button variant="outline">
              <X className="h-4 w-4" /> <span className="hidden sm:inline">取消</span>
            </Button>
            <Button>
              <Save className="h-4 w-4" /> <span className="hidden sm:inline">保存</span>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr] items-start">
        <nav className="sticky top-[76px] grid gap-1">
          {SECTIONS.map((s, i) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className={`rounded-md px-3 py-2 text-sm transition-colors ${
                i === 0 ? "bg-accent-500/12 text-foreground" : "text-muted-foreground hover:bg-white/[0.04]"
              }`}
            >
              {s.label}
            </a>
          ))}
        </nav>

        <SettingsForm />
      </section>
    </>
  );
}
