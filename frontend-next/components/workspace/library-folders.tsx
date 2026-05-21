"use client";

import { useState } from "react";
import { Folder, Video, Image as ImageIcon, Music2, Type, Palette, type LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type FolderDef = {
  id: string;
  label: string;
  icon: LucideIcon;
  count: number;
};

export function LibraryFolders({ totals, totalAll }: { totals: Record<string, number>; totalAll: number }) {
  const folders: FolderDef[] = [
    { id: "all", label: "全部素材", icon: Folder, count: totalAll },
    { id: "video", label: "视频", icon: Video, count: totals.video ?? 0 },
    { id: "image", label: "图片", icon: ImageIcon, count: totals.image ?? 0 },
    { id: "audio", label: "音频", icon: Music2, count: totals.audio ?? 0 },
    { id: "font", label: "字体", icon: Type, count: totals.font ?? 0 },
    { id: "logo", label: "品牌", icon: Palette, count: totals.logo ?? 0 },
  ];

  const [active, setActive] = useState(folders[0].id);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">文件夹</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-1 p-2">
        <div role="toolbar" aria-label="按类型过滤素材" className="grid gap-1">
          {folders.map((f) => {
            const Icon = f.icon;
            const isActive = active === f.id;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => setActive(f.id)}
                aria-pressed={isActive}
                className={cn(
                  "flex items-center gap-3 rounded-md px-2.5 py-2 text-sm transition-colors",
                  isActive ? "bg-accent-500/12 text-foreground" : "text-muted-foreground hover:bg-white/[0.04]"
                )}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden />
                {f.label}
                <span className="ml-auto font-mono text-[11px] text-muted-foreground num">{f.count}</span>
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
