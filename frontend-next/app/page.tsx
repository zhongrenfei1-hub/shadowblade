import Link from "next/link";
import { ArrowRight, Sparkles, ShieldCheck, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/brand/brand-mark";

/**
 * 公开访客入口 / marketing 极简 hero。
 *
 * 历史上这里 `redirect("/dashboard")` 会把分享链接 footer / logo 点过来的外部访客
 * 直接送进 (app) layout（带 sidebar），违和。
 * 现在改成极简 marketing hero：员工点「进入工作台」走 (app)，外部访客留在这里。
 *
 * 是 RSC，0 JS。
 */
export default function RootPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border/60">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3 md:px-6">
          <BrandMark className="h-8 w-8" />
          <span className="font-display text-base font-semibold tracking-tight">ShadowBlade</span>
          <Button asChild variant="outline" size="sm" className="ml-auto">
            <Link href="/dashboard">进入工作台</Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto grid max-w-5xl gap-10 px-4 py-12 md:px-6 md:py-20">
        <section className="grid gap-4">
          <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
            企业级 AI 视频云
          </span>
          <h1 className="font-display text-[34px] font-semibold tracking-tight md:text-[52px]">
            一份简报，<br className="hidden sm:inline" />四分钟出片。
          </h1>
          <p className="max-w-2xl text-base text-muted-foreground md:text-lg">
            ShadowBlade 把一份简报变成可以直接上线的营销 / 培训 / 产品视频。
            对照你的品牌套件渲染，全程对齐审核与合规。
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Button asChild size="lg">
              <Link href="/dashboard">
                进入工作台 <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/create">看一次创建流程</Link>
            </Button>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-3">
          {[
            { icon: Sparkles, title: "4 分钟出片", desc: "从简报到 MP4，6 步混剪流水线全自动。" },
            { icon: ShieldCheck, title: "品牌不漂移", desc: "对照品牌套件渲染，每条成片有偏移评分。" },
            { icon: Clock, title: "审核闭环", desc: "签名链接 / 审计日志 / 角色权限一并交付。" },
          ].map((f) => (
            <div
              key={f.title}
              className="grid gap-2 rounded-xl border border-border bg-card/60 p-5"
            >
              <span className="grid h-9 w-9 place-items-center rounded-md border border-accent-500/30 bg-accent-500/10 text-accent-300">
                <f.icon className="h-4 w-4" aria-hidden />
              </span>
              <h2 className="font-display text-base font-semibold">{f.title}</h2>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </section>
      </main>

      <footer className="border-t border-border bg-background/60 py-6">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 px-4 text-xs text-muted-foreground md:px-6">
          <span>© ShadowBlade · 企业级 AI 视频云</span>
          <span className="ml-auto">
            <a className="hover:text-foreground" href="mailto:hello@shadowblade.io">联系我们</a>
          </span>
        </div>
      </footer>
    </div>
  );
}
