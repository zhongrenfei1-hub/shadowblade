"use client";

import { useState } from "react";
import { Wand2, SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { StudioGenerate } from "@/components/workspace/studio-generate";
import { StudioWorkbench } from "@/components/workspace/studio-workbench";

type Mode = "ai" | "manual";

export function StudioModeSwitch() {
  const [mode, setMode] = useState<Mode>("ai");
  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <ModeButton
          active={mode === "ai"}
          onClick={() => setMode("ai")}
          icon={<Wand2 size={14} />}
          label="AI 一键生成"
          hint="主题 → 脚本 → 配音 → 字幕 → 混剪 → MP4"
        />
        <ModeButton
          active={mode === "manual"}
          onClick={() => setMode("manual")}
          icon={<SlidersHorizontal size={14} />}
          label="手动混剪"
          hint="直接控制素材、字幕脚本、过渡风格"
        />
      </div>

      {mode === "ai" ? <StudioGenerate /> : <StudioWorkbench />}
    </>
  );
}

function ModeButton({
  active,
  onClick,
  icon,
  label,
  hint,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  hint: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex items-start gap-3 rounded-lg border px-4 py-3 text-left transition-colors",
        active
          ? "border-accent-500/60 bg-accent-500/10"
          : "border-white/10 bg-white/[0.02] hover:border-white/20",
      )}
    >
      <span
        className={cn(
          "mt-0.5 shrink-0",
          active ? "text-accent-300" : "text-muted-foreground group-hover:text-foreground",
        )}
      >
        {icon}
      </span>
      <span className="grid gap-0.5">
        <span className={cn("text-sm font-semibold", active ? "text-accent-200" : "text-foreground")}>
          {label}
        </span>
        <span className="text-[11px] text-muted-foreground">{hint}</span>
      </span>
    </button>
  );
}
