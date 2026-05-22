import { headers } from "next/headers";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type InvitationPublic,
  inspectInvitation,
} from "@/lib/api/organizations";
import { InviteAccept } from "@/components/workspace/invite-accept";

/**
 * Server-side preflight for ``/invite/[code]``.
 *
 * The lookup is public so we don't gate the page on auth. If the code
 * doesn't exist or has expired/been revoked, we render an explanatory
 * error card instead of the accept form.
 */
async function loadInvite(
  code: string,
): Promise<
  | { invite: InvitationPublic; error: null }
  | { invite: null; error: string }
> {
  headers(); // opt out of static rendering (per-request)
  try {
    const invite = await inspectInvitation(code);
    return { invite, error: null };
  } catch (err) {
    return {
      invite: null,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

const ROLE_LABEL: Record<string, string> = {
  owner: "拥有者",
  admin: "管理员",
  member: "编辑",
  guest: "查看者",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "等待你接受",
  accepted: "已被接受",
  revoked: "已被撤销",
  expired: "已过期",
};

export default async function InvitePage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const { invite, error } = await loadInvite(code);

  if (error || !invite) {
    return (
      <section className="grid place-items-center py-16">
        <Card className="w-full max-w-lg border-destructive/40 bg-destructive/5">
          <CardHeader>
            <CardTitle className="text-destructive">
              邀请链接无效
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm">
            <p>没有找到这枚邀请码，或者链接已被撤销。</p>
            <code className="font-mono text-xs text-destructive">
              {error}
            </code>
            <p className="text-muted-foreground">
              如果你确定刚收到链接，请联系发起邀请的管理员重新生成。
            </p>
          </CardContent>
        </Card>
      </section>
    );
  }

  if (invite.status !== "pending") {
    return (
      <section className="grid place-items-center py-16">
        <Card className="w-full max-w-lg">
          <CardHeader>
            <CardTitle>邀请{STATUS_LABEL[invite.status] ?? invite.status}</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            <p>
              这份发给 <b>{invite.email}</b> 的邀请已经
              <b>{STATUS_LABEL[invite.status]}</b>，无法再次接受。
            </p>
            <p className="text-muted-foreground">
              如需重新加入团队 <b>{invite.workspace_name}</b>
              ，请让管理员重新发送邀请。
            </p>
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <section className="grid place-items-center py-12">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>你被邀请加入「{invite.workspace_name}」</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-1 rounded-md border border-border bg-card/40 p-4 text-sm">
            <div className="flex items-baseline justify-between">
              <span className="text-muted-foreground">邀请发送至</span>
              <b>{invite.email}</b>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-muted-foreground">入团角色</span>
              <b>{ROLE_LABEL[invite.role] ?? invite.role}</b>
            </div>
            <div className="flex items-baseline justify-between">
              <span className="text-muted-foreground">过期时间</span>
              <b>{new Date(invite.expires_at).toLocaleString("zh-CN")}</b>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            点击下方按钮即可接受。如果该邮箱还没有 ShadowBlade
            账号，系统会在接受流程里同时创建账号。
          </p>
          <InviteAccept code={code} expectedEmail={invite.email} />
        </CardContent>
      </Card>
    </section>
  );
}
