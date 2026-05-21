"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

type Section = { id: string; label: string };

export function SettingsNav({ sections }: { sections: Section[] }) {
  const [activeId, setActiveId] = useState<string>(sections[0]?.id ?? "");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const targets = sections
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => el !== null);
    if (targets.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActiveId(visible.target.id);
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.1, 0.25, 0.5] }
    );
    targets.forEach((el) => observer.observe(el));

    // 初始化：根据 hash 或第一个 section
    if (window.location.hash) {
      const initial = window.location.hash.slice(1);
      if (sections.some((s) => s.id === initial)) setActiveId(initial);
    }

    return () => observer.disconnect();
  }, [sections]);

  return (
    <nav className="sticky top-[76px] grid gap-1" aria-label="设置分区">
      {sections.map((s) => {
        const active = activeId === s.id;
        return (
          <a
            key={s.id}
            href={`#${s.id}`}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-md px-3 py-2 text-sm transition-colors",
              active ? "bg-accent-500/12 text-foreground" : "text-muted-foreground hover:bg-white/[0.04]"
            )}
          >
            {s.label}
          </a>
        );
      })}
    </nav>
  );
}
