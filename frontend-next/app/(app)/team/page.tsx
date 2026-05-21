import React from "react";
import { UserPlus, Users, ShieldCheck, Clock, Activity, Mail, Crown } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { KpiTile } from "@/components/workspace/kpi-tile";
import { cn } from "@/lib/utils";

const ROLE_VARIANT: Record<string, BadgeProps["variant"]> = {
  "工作空间管理员": "done",
  "制作人": "rendering",
  "品牌负责人": "review",
  "审核员": "queued",
};

type Permission = {
  label: string;
  admin: boolean;
  producer: boolean;
  brand: boolean;
  reviewer: boolean;
  viewer: boolean;
};

const PERMISSIONS: Permission[] = [
  { label: "渲染视频", admin: true, producer: true, brand: true, reviewer: false, viewer: false },
  { label: "批准 / 发布", admin: true, producer: false, brand: true, reviewer: true, viewer: false },
  { label: "编辑品牌套件", admin: true, producer: false, brand: true, reviewer: false, viewer: false },
  { label: "管理席位", admin: true, producer: false, brand: false, reviewer: false, viewer: false },
  { label: "查看分析", admin: true, producer: true, brand: true, reviewer: true, viewer: true },
  { label: "导出 / 下载", admin: true, producer: true, brand: true, reviewer: true, viewer: false },
];

const ROLES: { key: keyof Omit<Permission, "label">; label: string }[] = [
  { key: "admin", label: "管理员" },
  { key: "producer", label: "制作人" },
  { key: "brand", label: "品牌" },
  { key: "reviewer", label: "审核员" },
  { key: "viewer", label: "只读" },
];

const PRESENCE_LABEL: Record<string, string> = {
  online: "在线",
  idle: "离开",
  offline: "离线",
};

const PRESENCE_COLOR: Record<string, string> = {
  online: "bg-accent-400 shadow-[0_0_8px_rgba(34,211,183,0.55)]",
  idle: "bg-amber-400",
  offline: "bg-graphite-300/60",
};

const RECENT_ACTIVITY: Record<number, string> = {
  1: "刚刚批准 v17 渲染",
  2: "上传了「春日空镜」18 段素材",
  3: "更新品牌套件 v3 字体",
  4: "审批 12 条待发布成片",
};

function initials(name: string) {
  return name
    .split(" ")
    .map((s) => s[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export default async function TeamPage() {
  const ws = await api.workspace();
  const onlineCount = ws.team.filter((m) => m.presence === "online").length;

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          工作空间 · 24 席用满 24
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">团队与权限</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              SSO 走 Okta，SCIM 每小时同步。当前 <b className="text-accent-300 num">{onlineCount}</b> 人在线，审核员审批通过后才能发布。
            </p>
          </div>
          <Button>
            <UserPlus className="h-4 w-4" /> <span className="hidden sm:inline">邀请成员</span><span className="sm:hidden">邀请</span>
          </Button>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <KpiTile icon={Users} label="席位" value="24" suffix="/ 24" delta="100% 已用" trend={[18, 19, 21, 22, 23, 24, 24]} />
        <KpiTile icon={ShieldCheck} label="SSO" value="Okta" delta="SAML 2.0 已强制" trend={[1, 1, 1, 1, 1, 1, 1]} />
        <KpiTile icon={Clock} label="待邀请" value="2" delta="5 天后失效" positive={false} trend={[5, 4, 4, 3, 3, 2, 2]} />
        <KpiTile icon={Activity} label="审计日志" value="实时" delta="最新事件 12 秒前" trend={[3, 5, 4, 6, 8, 7, 9]} />
      </section>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <CardTitle>成员</CardTitle>
            <Badge variant="default">共 {ws.team.length} 人</Badge>
            <span className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-400 shadow-[0_0_6px_rgba(34,211,183,0.6)]" aria-hidden />
              {onlineCount} 在线
            </span>
          </div>
          <Button size="sm" variant="outline">导出 CSV</Button>
        </CardHeader>
        <CardContent>
          {/* 移动端：卡片列表 */}
          <div className="grid gap-3 md:hidden">
            {ws.team.map((m) => {
              const presence = m.presence ?? "offline";
              return (
                <div key={m.id} className="grid gap-3 rounded-md border border-border bg-card/40 p-4">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <Avatar>
                        <AvatarFallback>{initials(m.name)}</AvatarFallback>
                      </Avatar>
                      <span
                        aria-label={PRESENCE_LABEL[presence]}
                        className={cn(
                          "absolute -right-0.5 -bottom-0.5 h-2.5 w-2.5 rounded-full ring-2 ring-card",
                          PRESENCE_COLOR[presence]
                        )}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <b className="truncate font-semibold">{m.name}</b>
                        {m.role === "工作空间管理员" && <Crown className="h-3 w-3 text-accent-300" aria-hidden />}
                      </div>
                      <span className="truncate text-[11px] text-muted-foreground">
                        {m.email ?? `${m.name.toLowerCase().replace(/\s+/g, ".")}@acme.com`}
                      </span>
                    </div>
                    <Badge variant={ROLE_VARIANT[m.role] ?? "default"}>{m.role}</Badge>
                  </div>
                  <div className="flex items-center justify-between border-t border-border pt-2 text-[11px] text-muted-foreground">
                    <span className="truncate">{RECENT_ACTIVITY[m.id] ?? "—"}</span>
                    <span className="num">{m.last_active ?? "—"}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* 桌面：表格 */}
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-white/[0.02] text-[10px] uppercase tracking-wider text-muted-foreground">
                  <th className="px-4 py-2 text-left font-semibold">成员</th>
                  <th className="px-4 py-2 text-left font-semibold">角色</th>
                  <th className="px-4 py-2 text-left font-semibold">最近动作</th>
                  <th className="px-4 py-2 text-left font-semibold">活跃</th>
                  <th className="px-4 py-2 text-left font-semibold">登录</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {ws.team.map((m) => {
                  const presence = m.presence ?? "offline";
                  return (
                    <tr key={m.id} className="border-b border-border last:border-0 transition-colors hover:bg-white/[0.025]">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="relative">
                            <Avatar>
                              <AvatarFallback>{initials(m.name)}</AvatarFallback>
                            </Avatar>
                            <span
                              aria-label={PRESENCE_LABEL[presence]}
                              title={PRESENCE_LABEL[presence]}
                              className={cn(
                                "absolute -right-0.5 -bottom-0.5 h-2.5 w-2.5 rounded-full ring-2 ring-card",
                                PRESENCE_COLOR[presence]
                              )}
                            />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <b className="block font-semibold">{m.name}</b>
                              {m.role === "工作空间管理员" && (
                                <Crown className="h-3 w-3 text-accent-300" aria-label="管理员" />
                              )}
                            </div>
                            <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                              <Mail className="h-2.5 w-2.5 opacity-60" aria-hidden />
                              {m.email ?? `${m.name.toLowerCase().replace(/\s+/g, ".")}@acme.com`}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={ROLE_VARIANT[m.role] ?? "default"}>{m.role}</Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {RECENT_ACTIVITY[m.id] ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-[11px] text-muted-foreground num">{m.last_active ?? "—"}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">SSO · Okta</td>
                      <td className="px-4 py-3 text-right">
                        <Button size="sm" variant="outline">管理</Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>角色与权限矩阵</CardTitle>
          <p className="text-sm text-muted-foreground">● 允许 · ○ 拒绝。改动会同步给 SCIM 下游系统。</p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <div
              className="grid min-w-[640px]"
              style={{ gridTemplateColumns: "240px repeat(5, 1fr)" }}
            >
              <div className="border-b border-border py-3" />
              {ROLES.map((r) => (
                <div
                  key={r.key}
                  className="border-b border-border py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-muted-foreground"
                >
                  {r.label}
                </div>
              ))}
              {PERMISSIONS.map((perm) => (
                <React.Fragment key={perm.label}>
                  <div className="border-b border-border py-3 text-sm font-semibold">{perm.label}</div>
                  {ROLES.map((r) => {
                    const on = perm[r.key];
                    return (
                      <div
                        key={`${perm.label}-${r.key}`}
                        className={cn(
                          "border-b border-border py-3 text-center font-mono text-sm transition-colors",
                          on ? "text-accent-300" : "text-muted-foreground opacity-40"
                        )}
                      >
                        {on ? "●" : "○"}
                      </div>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
