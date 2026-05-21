/**
 * 主导航单一来源
 * sidebar（桌面常驻） + mobile-sidebar（抽屉） + topbar ROUTE_LABEL（面包屑）
 * 都从这里取值，避免三处分别维护。
 */

import {
  LayoutDashboard,
  Sparkles,
  FolderOpen,
  Library,
  Palette,
  LayoutTemplate,
  Users,
  Settings,
  LineChart,
  Plug,
  Bell,
  Film,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  /** 主 CTA · 在 sidebar 显示闪电图标。 */
  cta?: boolean;
  /** 仅显示的 badge 数字（如项目计数）。仅装饰用，业务数据接通后再热更。 */
  badge?: string;
};

export type NavGroup = {
  group: string;
  items: NavItem[];
};

export const NAV: NavGroup[] = [
  {
    group: "制作",
    items: [
      { href: "/dashboard", label: "工作台", icon: LayoutDashboard },
      { href: "/create", label: "新建视频", icon: Sparkles, cta: true },
      { href: "/studio", label: "Studio · 真混剪", icon: Film },
      { href: "/projects", label: "项目库", icon: FolderOpen, badge: "38" },
      { href: "/templates", label: "模板", icon: LayoutTemplate },
      { href: "/analytics", label: "数据分析", icon: LineChart },
    ],
  },
  {
    group: "素材与品牌",
    items: [
      { href: "/library", label: "素材库", icon: Library },
      { href: "/brand", label: "品牌套件", icon: Palette },
    ],
  },
  {
    group: "工作空间",
    items: [
      { href: "/team", label: "团队", icon: Users },
      { href: "/integrations", label: "集成", icon: Plug },
      { href: "/notifications", label: "通知", icon: Bell },
      { href: "/settings", label: "设置", icon: Settings },
    ],
  },
];

/** 面包屑 / 页头 fallback 显示。
 *  当 pathname `/{slug}` 在此映射中时显示中文名，否则 fallback 到 slug 本身。 */
export const ROUTE_LABEL: Record<string, string> = Object.fromEntries(
  NAV.flatMap((g) => g.items).map((i) => [i.href, i.label])
);
