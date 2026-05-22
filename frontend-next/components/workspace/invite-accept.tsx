"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";
import {
  acceptInvitation,
  authMe,
  type AuthMe,
} from "@/lib/api/organizations";
import { Button } from "@/components/ui/button";

interface Props {
  /** The 32-char invite code from the URL. */
  code: string;
  /** The email the invite was issued to — shown for confirmation. */
  expectedEmail: string;
}

/**
 * Client island that handles the actual ``POST /invitations/{code}/accept``
 * round-trip. Kept separate from the server-rendered detail card so the
 * preflight can stay in a Server Component and the button can pull in
 * the auth-bootstrap module without leaking it into the static HTML.
 *
 * Note on auth: the underlying ``acceptInvitation`` call goes through
 * the same demo login/register bootstrap as the rest of the org client.
 * If the current logged-in email doesn't match the invitation's
 * ``expected_email`` the backend returns 403 ("invitation was issued
 * to a different email"); we surface that with a remediation hint.
 */
export function InviteAccept({ code, expectedEmail }: Props) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [error, setError] = useState<string | null>(null);
  const [me, setMe] = useState<AuthMe["user"] | null>(null);

  async function handleAccept() {
    setState("busy");
    setError(null);
    try {
      const meResp = await authMe();
      setMe(meResp.user);
      if (meResp.user.email.toLowerCase() !== expectedEmail.toLowerCase()) {
        setError(
          `当前登录的是 ${meResp.user.email}，但邀请发给的是 ${expectedEmail}。` +
            `请先用 ${expectedEmail} 注册或登录。`,
        );
        setState("idle");
        return;
      }
      const accepted = await acceptInvitation(code);
      setState("done");
      // Give the success card a beat, then drop the user on the team page.
      setTimeout(() => {
        router.push(`/team?ws=${accepted.workspace_id}`);
      }, 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setState("idle");
    }
  }

  if (state === "done") {
    return (
      <div className="grid gap-3 rounded-md border border-emerald-500/40 bg-emerald-500/5 p-4 text-sm">
        <div className="flex items-center gap-2 text-emerald-300">
          <CheckCircle2 className="h-5 w-5" aria-hidden />
          <b>已加入团队！</b>
        </div>
        <p className="text-muted-foreground">即将跳转到团队页…</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 font-mono text-xs text-destructive">
          {error}
        </div>
      )}
      <Button onClick={handleAccept} disabled={state === "busy"}>
        {state === "busy" ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : null}
        <span>接受邀请并加入团队</span>
      </Button>
      {me && (
        <p className="text-[11px] text-muted-foreground">
          当前登录: {me.email}
        </p>
      )}
    </div>
  );
}
