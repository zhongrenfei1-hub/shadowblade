import { headers } from "next/headers";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TeamEditor } from "@/components/workspace/team-editor";
import {
  listInvitations,
  listMembers,
  listOrganizations,
} from "@/lib/api/organizations";

async function loadTeam() {
  headers();
  try {
    const orgs = await listOrganizations();
    if (orgs.length === 0) {
      return { error: "当前账号还没有任何组织", org: null, members: [], invitations: [] };
    }
    const org = orgs[0];
    const [members, invitations] = await Promise.all([
      listMembers(org.id),
      listInvitations(org.id),
    ]);
    return { org, members, invitations, error: null };
  } catch (err) {
    return {
      org: null,
      members: [],
      invitations: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export default async function TeamPage() {
  const { org, members, invitations, error } = await loadTeam();

  if (error || !org) {
    return (
      <section className="grid gap-4">
        <h1 className="font-display text-2xl font-semibold">团队</h1>
        <Card className="border-destructive/40 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">无法加载团队</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-mono text-xs text-destructive">{error}</p>
            <p className="mt-3 text-sm text-muted-foreground">
              本页面会自动 demo 登录 (demo@example.com / demo1234) 拿 JWT。
              请确认 backend :8000 已起，并且 /api/v1/auth/register 可用。
            </p>
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          团队
        </span>
        <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
          {org.name}
        </h1>
        <p className="max-w-prose text-sm text-muted-foreground">
          管理成员、角色和邀请。所有改动实时同步到 /api/v1/organizations/{org.id}。
        </p>
      </section>

      <TeamEditor
        org={org}
        initialMembers={members}
        initialInvitations={invitations}
      />
    </>
  );
}
