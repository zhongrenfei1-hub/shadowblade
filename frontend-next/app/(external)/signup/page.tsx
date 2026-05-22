"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthApiError, register, saveSession } from "@/lib/api/auth";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [fullName, setFullName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setError("密码至少 8 位");
      return;
    }
    if (password !== confirm) {
      setError("两次输入的密码不一致");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const resp = await register(email, password, fullName.trim());
      saveSession(resp);
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof AuthApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "注册失败",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-accent-500/10 via-background to-background px-4 py-12">
      <div className="grid w-full max-w-md gap-6">
        <div className="grid gap-2 text-center">
          <Link
            href="/"
            className="inline-grid place-items-center font-display text-3xl font-bold tracking-tight"
          >
            ShadowBlade
          </Link>
          <p className="text-sm text-muted-foreground">
            60 秒注册，自动建一个 workspace
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>创建账号</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              系统会自动为你创建一个名为「你的名字 的团队」的 workspace。
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="grid gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="signup-name" className="text-xs">姓名</Label>
                <Input
                  id="signup-name"
                  required
                  minLength={2}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ava Chen"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="signup-email" className="text-xs">邮箱</Label>
                <Input
                  id="signup-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
                <span className="text-[10px] text-muted-foreground">
                  注意：.local 等保留域名不被接受，请用真实邮箱域。
                </span>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="signup-password" className="text-xs">密码</Label>
                <Input
                  id="signup-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <span className="text-[10px] text-muted-foreground">
                  至少 8 位
                </span>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="signup-confirm" className="text-xs">
                  确认密码
                </Label>
                <Input
                  id="signup-confirm"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </div>

              {error && (
                <p
                  role="alert"
                  className="rounded-md border border-destructive/40 bg-destructive/5 p-3 font-mono text-xs text-destructive"
                >
                  {error}
                </p>
              )}

              <Button type="submit" disabled={busy} className="w-full">
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : (
                  <UserPlus className="h-4 w-4" aria-hidden />
                )}
                <span>创建账号</span>
              </Button>
            </form>

            <div className="mt-6 grid gap-3 border-t border-border pt-6 text-center text-xs text-muted-foreground">
              <span>
                已经有账号？{" "}
                <Link
                  href="/login"
                  className="font-semibold text-accent-300 hover:underline"
                >
                  直接登录
                </Link>
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
