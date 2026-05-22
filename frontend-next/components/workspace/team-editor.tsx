"use client";

import { useEffect, useState, useTransition } from "react";
import { Check, Copy, Loader2, Mail, Trash2, UserPlus } from "lucide-react";
import {
  type Invitation,
  type Member,
  type Organization,
  type Role,
  authMe,
  inviteMember,
  listInvitations,
  listMembers,
  removeMember,
  revokeInvitation,
  updateMemberRole,
} from "@/lib/api/organizations";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// Canonical backend roles. The UI keeps the historical "编辑/查看者"
// Chinese labels so existing users aren't surprised by a rename, but the
// values posted to the API are the canonical names — the backend also
// accepts the legacy ``editor``/``viewer`` aliases (see
// app/core/permissions.py) for cross-version safety.
const ROLE_LABEL: Record<Role, string> = {
  owner: "拥有者",
  admin: "管理员",
  member: "编辑",
  guest: "查看者",
};

const ROLE_VARIANT: Record<Role, "done" | "rendering" | "review" | "draft"> = {
  owner: "done",
  admin: "rendering",
  member: "review",
  guest: "draft",
};

// Roles that an admin/owner can assign to a new invite. ``owner`` is
// reserved (transfer only); the others mirror the backend
// :data:`app.schemas.invitation.InviteRole`.
const INVITE_ROLES: Role[] = ["admin", "member", "guest"];
const ALL_ROLES: Role[] = ["owner", "admin", "member", "guest"];

interface Props {
  org: Organization;
  initialMembers: Member[];
  initialInvitations: Invitation[];
  /** Initial "current user" id from server-side render; client refines. */
  initialCurrentUserId?: number | null;
}

export function TeamEditor({
  org,
  initialMembers,
  initialInvitations,
  initialCurrentUserId,
}: Props) {
  const [members, setMembers] = useState(initialMembers);
  const [invitations, setInvitations] = useState(initialInvitations);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("member");
  const [busy, setBusy] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [currentUserId, setCurrentUserId] = useState<number | null>(
    initialCurrentUserId ?? null,
  );
  const [lastIssued, setLastIssued] = useState<Invitation | null>(null);
  const [, startTransition] = useTransition();

  // Resolve "who am I" from /auth/me so the per-row self-protection
  // logic compares against the *caller* rather than the org owner.
  useEffect(() => {
    if (currentUserId !== null) return;
    let cancelled = false;
    authMe()
      .then((me) => {
        if (!cancelled) setCurrentUserId(me.user.id);
      })
      .catch(() => {
        // Auth bootstrap failures already surface elsewhere; don't
        // re-spam the inline error here.
      });
    return () => {
      cancelled = true;
    };
  }, [currentUserId]);

  async function refresh() {
    const [m, i] = await Promise.all([
      listMembers(org.id),
      listInvitations(org.id),
    ]);
    setMembers(m);
    setInvitations(i);
  }

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!inviteEmail.includes("@")) {
      setErrorMsg("邮箱格式不对");
      return;
    }
    setBusy("invite");
    setErrorMsg(null);
    try {
      const created = await inviteMember(org.id, inviteEmail, inviteRole);
      setLastIssued(created);
      setInviteEmail("");
      setInviteRole("member");
      startTransition(refresh);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleRoleChange(userId: number, role: Role) {
    setBusy(`role-${userId}`);
    setErrorMsg(null);
    try {
      await updateMemberRole(org.id, userId, role);
      setMembers((ms) =>
        ms.map((m) => (m.user_id === userId ? { ...m, role } : m)),
      );
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleRemoveMember(userId: number) {
    if (!confirm("确认从团队移除该成员？")) return;
    setBusy(`remove-${userId}`);
    setErrorMsg(null);
    try {
      await removeMember(org.id, userId);
      setMembers((ms) => ms.filter((m) => m.user_id !== userId));
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleRevoke(inviteId: number) {
    setBusy(`revoke-${inviteId}`);
    setErrorMsg(null);
    try {
      await revokeInvitation(org.id, inviteId);
      setInvitations((is) => is.filter((i) => i.id !== inviteId));
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  function buildInviteLink(code: string): string {
    if (typeof window === "undefined") return `/invite/${code}`;
    return `${window.location.origin}/invite/${code}`;
  }

  async function handleCopy(code: string) {
    const link = buildInviteLink(code);
    try {
      await navigator.clipboard.writeText(link);
      setCopiedCode(code);
      setTimeout(
        () => setCopiedCode((c) => (c === code ? null : c)),
        2000,
      );
    } catch {
      setErrorMsg("浏览器不允许写剪贴板，请手动复制邀请链接");
    }
  }

  // A pending invite is one that hasn't been accepted/revoked/expired
  // by the server. We filter on the wire status so a refresh doesn't
  // surprise the user with a "live" invite they thought was gone.
  const pendingInvitations = invitations.filter((i) => i.status === "pending");

  return (
    <div className="grid gap-6">
      {errorMsg && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="p-4 font-mono text-xs text-destructive">
            {errorMsg}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{org.name}</CardTitle>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {org.plan} · {org.member_count} 人 · 月渲染{" "}
              {org.monthly_render_used}/{org.monthly_render_quota}
            </p>
          </div>
          <Badge variant={ROLE_VARIANT[org.role]}>
            你是{ROLE_LABEL[org.role]}
          </Badge>
        </CardHeader>
      </Card>

      {/* Invite issuance success — surface the link prominently. */}
      {lastIssued && (
        <Card className="border-emerald-500/40 bg-emerald-500/5">
          <CardHeader>
            <CardTitle className="text-emerald-300">
              邀请已生成 — 发送以下链接给 {lastIssued.email}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3">
            <code className="block break-all rounded-md border border-emerald-500/30 bg-background p-3 font-mono text-xs">
              {buildInviteLink(lastIssued.invite_code)}
            </code>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => handleCopy(lastIssued.invite_code)}
                size="sm"
                variant="outline"
              >
                {copiedCode === lastIssued.invite_code ? (
                  <Check className="h-4 w-4" aria-hidden />
                ) : (
                  <Copy className="h-4 w-4" aria-hidden />
                )}
                <span>
                  {copiedCode === lastIssued.invite_code
                    ? "已复制"
                    : "复制邀请链接"}
                </span>
              </Button>
              <Button
                onClick={() => setLastIssued(null)}
                size="sm"
                variant="outline"
              >
                关闭
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              过期于 {new Date(lastIssued.expires_at).toLocaleString("zh-CN")} ·
              角色: {ROLE_LABEL[lastIssued.role]}
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>成员（{members.length}）</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-2">
            {members.map((m) => {
              // Self-protection: the *current caller* can't change their own
              // row without going through /transfer or "leave organization".
              // Comparing against the *org owner* would have locked the
              // wrong member (an admin viewing a non-owned org).
              const isSelf =
                currentUserId !== null && m.user_id === currentUserId;
              return (
                <div
                  key={m.id}
                  className="grid grid-cols-[1fr_140px_44px] items-center gap-3 rounded-md border border-border bg-card/40 p-3"
                >
                  <div className="grid leading-tight">
                    <b className="text-sm">{m.user.full_name}</b>
                    <span className="text-[11px] text-muted-foreground">
                      user #{m.user_id} · 加入于{" "}
                      {new Date(m.joined_at).toLocaleDateString("zh-CN")}
                      {isSelf && " · 你"}
                    </span>
                  </div>
                  <select
                    aria-label={`${m.user.full_name} 角色`}
                    value={m.role}
                    disabled={busy === `role-${m.user_id}` || isSelf}
                    onChange={(e) =>
                      handleRoleChange(m.user_id, e.target.value as Role)
                    }
                    className="h-9 rounded-md border border-border bg-background px-2 text-sm"
                  >
                    {ALL_ROLES.map((r) => (
                      <option key={r} value={r}>
                        {ROLE_LABEL[r]}
                      </option>
                    ))}
                  </select>
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={isSelf || busy === `remove-${m.user_id}`}
                    onClick={() => handleRemoveMember(m.user_id)}
                    aria-label="移除成员"
                  >
                    {busy === `remove-${m.user_id}` ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Trash2 className="h-4 w-4" aria-hidden />
                    )}
                  </Button>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>邀请新成员</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleInvite}
            className="grid gap-3 sm:grid-cols-[1fr_180px_140px]"
          >
            <div className="grid gap-1">
              <Label htmlFor="invite-email" className="text-xs">
                邮箱
              </Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="alice@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-1">
              <Label htmlFor="invite-role" className="text-xs">
                角色
              </Label>
              <select
                id="invite-role"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as Role)}
                className="h-9 rounded-md border border-border bg-background px-2 text-sm"
              >
                {INVITE_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABEL[r]}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid items-end">
              <Button type="submit" disabled={busy === "invite"}>
                {busy === "invite" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <UserPlus className="h-4 w-4" aria-hidden />
                )}
                <span>发送邀请</span>
              </Button>
            </div>
          </form>
          <p className="mt-3 text-[11px] text-muted-foreground">
            邀请会生成一个一次性链接。生成后请把链接复制并发给受邀人 —
            受邀人用该邮箱登录后点击链接即可加入。系统暂不发送邮件。
          </p>
        </CardContent>
      </Card>

      {pendingInvitations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>
              待处理邀请（{pendingInvitations.length}）
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              {pendingInvitations.map((i) => (
                <div
                  key={i.id}
                  className="grid grid-cols-[24px_1fr_120px_44px_44px] items-center gap-3 rounded-md border border-border bg-card/40 p-3"
                >
                  <Mail
                    className="h-4 w-4 text-muted-foreground"
                    aria-hidden
                  />
                  <div className="grid leading-tight">
                    <b className="text-sm">{i.email}</b>
                    <span className="text-[11px] text-muted-foreground">
                      {ROLE_LABEL[i.role]} · 过期于{" "}
                      {new Date(i.expires_at).toLocaleDateString("zh-CN")}
                    </span>
                  </div>
                  <Badge variant={i.accepted_at ? "done" : "queued"}>
                    {i.accepted_at ? "已接受" : "待接受"}
                  </Badge>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleCopy(i.invite_code)}
                    aria-label="复制邀请链接"
                  >
                    {copiedCode === i.invite_code ? (
                      <Check className="h-4 w-4" aria-hidden />
                    ) : (
                      <Copy className="h-4 w-4" aria-hidden />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => handleRevoke(i.id)}
                    disabled={busy === `revoke-${i.id}`}
                    aria-label="撤销邀请"
                  >
                    {busy === `revoke-${i.id}` ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <Trash2 className="h-4 w-4" aria-hidden />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
