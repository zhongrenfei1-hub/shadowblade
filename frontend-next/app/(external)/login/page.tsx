"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, LogIn, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { AuthApiError, login, saveSession } from "@/lib/api/auth";

const DEMO_EMAIL = "demo@example.com";
const DEMO_PASSWORD = "demo1234";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const resp = await login(email, password);
      saveSession(resp);
      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof AuthApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "登录失败",
      );
    } finally {
      setBusy(false);
    }
  }

  function fillDemo() {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
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
            企业级 AI 短视频生成平台
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>登录</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              输入邮箱密码继续，或用 demo 账号一键试用。
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="grid gap-4">
              <div className="grid gap-1.5">
                <Label htmlFor="login-email" className="text-xs">邮箱</Label>
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="login-password" className="text-xs">密码</Label>
                <Input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
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
                  <LogIn className="h-4 w-4" aria-hidden />
                )}
                <span>登录</span>
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={fillDemo}
                className="w-full"
              >
                <ShieldCheck className="h-4 w-4" aria-hidden />
                <span>填入 demo 账号</span>
                <Badge variant="rendering">demo</Badge>
              </Button>
            </form>

            <div className="mt-6 grid gap-3 border-t border-border pt-6 text-center text-xs text-muted-foreground">
              <span>
                还没有账号？{" "}
                <Link
                  href="/signup"
                  className="font-semibold text-accent-300 hover:underline"
                >
                  注册新账号
                </Link>
              </span>
              <span>
                登录即同意{" "}
                <Link href="/about" className="hover:underline">
                  服务条款
                </Link>{" "}
                和{" "}
                <Link href="/about" className="hover:underline">
                  隐私政策
                </Link>
                。
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
