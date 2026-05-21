"use client";

import { useState } from "react";
import { Plus, ExternalLink, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Category = "all" | "connected" | "comms" | "cms" | "social" | "storage" | "crm" | "analytics" | "ops";

type Integration = {
  slug: string;
  name: string;
  cat: Exclude<Category, "all" | "connected">;
  desc: string;
  color: string;
  initials: string;
  connected?: boolean;
};

const INTEGRATIONS: Integration[] = [
  { slug: "slack", name: "Slack", cat: "comms", desc: "把渲染完成 / 待审批事件发到任意频道，emoji 一键批准。", color: "#4A154B", initials: "S", connected: true },
  { slug: "notion", name: "Notion", cat: "cms", desc: "从 Notion 数据库同步简报，成片回写到同一页面。", color: "#0f0f0f", initials: "N", connected: true },
  { slug: "figma", name: "Figma", cat: "cms", desc: "从 Figma 变量直接拉品牌套件，按夜里或发布触发。", color: "#F24E1E", initials: "F", connected: true },
  { slug: "youtube", name: "YouTube", cat: "social", desc: "成片以预约稿形式上传，章节和字幕沿用时间线。", color: "#FF0000", initials: "Y", connected: true },
  { slug: "linkedin", name: "LinkedIn", cat: "social", desc: "竖屏成片发到 Pages 与 Showcase。自动套品牌话术。", color: "#0A66C2", initials: "in", connected: true },
  { slug: "tiktok-business", name: "TikTok Business", cat: "social", desc: "9:16 成片作为付费创意素材推送，转化数据回流分析。", color: "#000000", initials: "d", connected: true },
  { slug: "premiere", name: "Adobe Premiere", cat: "cms", desc: "把时间线导出为 Premiere 工程，手动调最后 10%。", color: "#9999FF", initials: "Pr" },
  { slug: "after-effects", name: "After Effects", cat: "cms", desc: "把 AE 组合作为场景空镜，走 Aerender 无头渲染。", color: "#5555FF", initials: "Ae" },
  { slug: "drive", name: "Google Drive", cat: "storage", desc: "成片镜像到共享文件夹，便于内部分发。", color: "#0F9D58", initials: "D" },
  { slug: "sharepoint", name: "SharePoint", cat: "storage", desc: "成片和源素材发布到 SharePoint 文档库。", color: "#036C70", initials: "Sp" },
  { slug: "salesforce", name: "Salesforce", cat: "crm", desc: "商机推进到第四阶段时，自动触发定制成片。", color: "#00A1E0", initials: "SF" },
  { slug: "hubspot", name: "HubSpot", cat: "crm", desc: "在外发邮件里嵌入视频 CTA，跟踪点击率。", color: "#FF7A59", initials: "H" },
  { slug: "looker", name: "Looker", cat: "analytics", desc: "数据分析推到你仓库原生 dashboard 里。", color: "#4285F4", initials: "Lk" },
  { slug: "snowflake", name: "Snowflake", cat: "analytics", desc: "把渲染流水线每个事件流到 Snowflake，便于治理。", color: "#29B5E8", initials: "Sf" },
  { slug: "pagerduty", name: "PagerDuty", cat: "ops", desc: "渲染队列深度超过 SLA 阈值时给 oncall 报警。", color: "#06AC38", initials: "PD" },
];

const TABS: { id: Category; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "connected", label: "已连接" },
  { id: "comms", label: "沟通" },
  { id: "cms", label: "内容 / 设计" },
  { id: "social", label: "社交" },
  { id: "storage", label: "存储" },
  { id: "crm", label: "销售" },
  { id: "analytics", label: "分析" },
  { id: "ops", label: "运维" },
];

export default function IntegrationsPage() {
  const [tab, setTab] = useState<Category>("all");
  const [q, setQ] = useState("");

  // 先按 tab 收窄、再按搜索词过滤 — 不要把 connected 当成排他短路，否则 q 被吞掉。
  const list = INTEGRATIONS.filter((i) => {
    if (tab === "connected" && !i.connected) return false;
    if (tab !== "all" && tab !== "connected" && i.cat !== tab) return false;
    if (!q) return true;
    const needle = q.toLowerCase();
    return i.name.toLowerCase().includes(needle) || i.desc.toLowerCase().includes(needle);
  });

  const counts: Record<"all" | "connected", number> = {
    all: INTEGRATIONS.length,
    connected: INTEGRATIONS.filter((i) => i.connected).length,
  };

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">工作空间 · 集成市场</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              把 ShadowBlade 接到你的工具链里。
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              15 个开箱即用的集成，覆盖沟通 / CMS / 社交 / 存储 / 分析 / 身份。OAuth 或 API Key 鉴权，未授权前不碰你的成片数据。
            </p>
          </div>
          <Button>
            <Plus className="h-3.5 w-3.5" aria-hidden />
            自建一个
          </Button>
        </div>
      </section>

      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3 md:px-6">
          <label className="flex w-full items-center gap-2 rounded-md border border-border bg-card/70 px-3 py-1.5 text-sm focus-within:border-accent-500 md:w-[260px]">
            <Search className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
            <input
              aria-label="搜索集成"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="搜集成..."
              className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
            />
          </label>
          <div className="ml-auto flex flex-wrap gap-1.5" role="toolbar" aria-label="按分类过滤集成">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                aria-pressed={tab === t.id}
                className={cn(
                  "rounded-full border px-3 py-1 text-xs transition-colors",
                  tab === t.id
                    ? "border-accent-500/40 bg-accent-500/14 text-foreground"
                    : "border-border bg-card/40 text-muted-foreground hover:text-foreground"
                )}
              >
                {t.label}
                {(t.id === "all" || t.id === "connected") && (
                  <span className="ml-1.5 text-[10px] text-muted-foreground">{counts[t.id]}</span>
                )}
              </button>
            ))}
          </div>
        </div>

        <CardContent className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 md:p-6 lg:grid-cols-3">
          {list.map((i) => (
            <article
              key={i.slug}
              className={cn(
                "grid gap-3 rounded-lg border border-border bg-card/55 p-4 transition-all",
                "hover:-translate-y-0.5 hover:border-accent-500/40 hover:shadow-[0_8px_22px_-12px_rgba(34,211,183,0.35)]",
                i.connected && "border-accent-500/30"
              )}
            >
              <div className="flex items-start gap-3">
                <span
                  aria-hidden
                  className="grid h-11 w-11 shrink-0 place-items-center rounded-lg font-mono text-sm font-bold text-white"
                  style={{ background: i.color }}
                >
                  {i.initials}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <b className="font-display text-sm">{i.name}</b>
                    {i.connected && <Badge variant="done" className="text-[9px]">已连接</Badge>}
                  </div>
                  <span className="mt-0.5 block text-[10px] uppercase tracking-wider text-muted-foreground">
                    {TABS.find((t) => t.id === i.cat)?.label}
                  </span>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">{i.desc}</p>
              <div className="mt-1 flex items-center justify-between border-t border-border pt-3">
                <span className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span
                    className={cn(
                      "inline-block h-2 w-2 rounded-full",
                      i.connected ? "bg-accent-400" : "bg-graphite-500"
                    )}
                  />
                  {i.connected ? "已连接" : "未连接"}
                </span>
                <Button size="sm" variant={i.connected ? "outline" : "default"}>
                  {i.connected ? "配置" : "连接"}
                </Button>
              </div>
            </article>
          ))}
        </CardContent>

        {list.length === 0 && (
          <div className="grid place-items-center py-12 text-sm text-muted-foreground">
            没匹配到「{q || TABS.find((t) => t.id === tab)?.label || "全部"}」相关的集成。
          </div>
        )}
      </Card>

      <p className="text-center text-xs text-muted-foreground">
        没找到要的？
        <a className="ml-1 text-accent-300 hover:underline" href="https://api.shadowblade.io/v1" target="_blank" rel="noopener noreferrer">
          自己接 REST API
          <ExternalLink className="ml-1 inline h-3 w-3" aria-hidden />
        </a>
      </p>
    </>
  );
}
