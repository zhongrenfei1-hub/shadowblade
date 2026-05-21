import { UserPlus } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { KpiTile } from "@/components/workspace/kpi-tile";
import { Users, ShieldCheck, Clock, Activity } from "lucide-react";

const ROLE_VARIANT: Record<string, string> = {
  "工作空间管理员": "done",
  "制作人": "rendering",
  "品牌负责人": "review",
  "审核员": "queued",
};

const PERMISSIONS = [
  ["渲染视频", true, true, true, false, false],
  ["批准 / 发布", true, false, true, true, false],
  ["编辑品牌套件", true, false, true, false, false],
  ["管理席位", true, false, false, false, false],
  ["查看分析", true, true, true, true, true],
  ["导出 / 下载", true, true, true, true, false],
] as const;

const ROLES = ["管理员", "制作人", "品牌", "审核员", "只读"];

export default async function TeamPage() {
  const ws = await api.workspace();

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          工作空间 · 24 席用满 24
        </span>
        <div className="flex items-end gap-6">
          <div>
            <h1 className="font-display text-[34px] font-semibold tracking-tight">团队与权限</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              SSO 走 Okta，SCIM 每小时同步。18 位制作人、4 位审核员、2 位管理员。审核员审批通过后才能发布。
            </p>
          </div>
          <Button className="ml-auto">
            <UserPlus className="h-4 w-4" /> 邀请
          </Button>
        </div>
      </section>

      <section className="grid grid-cols-4 gap-4">
        <KpiTile icon={Users} label="席位" value="24" suffix="/ 24" delta="100% 已用" />
        <KpiTile icon={ShieldCheck} label="SSO" value="Okta" delta="SAML 2.0 已强制" />
        <KpiTile icon={Clock} label="待邀请" value="2" delta="5 天后失效" />
        <KpiTile icon={Activity} label="审计日志" value="实时" delta="最新事件 12 秒前" />
      </section>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>成员</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="default">共 {ws.team.length} 人</Badge>
            <Button size="sm" variant="outline">导出 CSV</Button>
          </div>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-white/[0.02] text-[10px] uppercase tracking-wider text-muted-foreground">
                <th className="px-4 py-2 text-left font-semibold">成员</th>
                <th className="px-4 py-2 text-left font-semibold">角色</th>
                <th className="px-4 py-2 text-left font-semibold">品牌套件</th>
                <th className="px-4 py-2 text-left font-semibold">最近活跃</th>
                <th className="px-4 py-2 text-left font-semibold">登录</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {ws.team.map((m) => (
                <tr key={m.id} className="border-b border-border last:border-0 hover:bg-white/[0.025]">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Avatar>
                        <AvatarFallback>{m.name.split(" ").map((s) => s[0]).join("").slice(0, 2)}</AvatarFallback>
                      </Avatar>
                      <div>
                        <b className="block font-semibold">{m.name}</b>
                        <span className="text-[11px] text-muted-foreground">
                          {m.name.toLowerCase().replace(" ", ".")}@acme.com
                        </span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={(ROLE_VARIANT[m.role] || "default") as never}>{m.role}</Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{m.id === 1 ? "全部" : "Core"}</td>
                  <td className="px-4 py-3 text-muted-foreground">2 分钟前</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">SSO · Okta</td>
                  <td className="px-4 py-3 text-right">
                    <Button size="sm" variant="outline">管理</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>角色与权限矩阵</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid" style={{ gridTemplateColumns: "240px repeat(5, 1fr)" }}>
            <div className="border-b border-border py-3" />
            {ROLES.map((r) => (
              <div key={r} className="border-b border-border py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {r}
              </div>
            ))}
            {PERMISSIONS.map(([label, ...cells]) => (
              <>
                <div key={String(label)} className="border-b border-border py-3 text-sm font-semibold">{label as string}</div>
                {(cells as boolean[]).map((on, i) => (
                  <div
                    key={i}
                    className={`border-b border-border py-3 text-center font-mono text-sm ${
                      on ? "text-accent-300" : "text-muted-foreground opacity-40"
                    }`}
                  >
                    {on ? "●" : "○"}
                  </div>
                ))}
              </>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}
