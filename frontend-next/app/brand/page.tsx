import { Plus, Check } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const KIT_META: Record<number, string> = {
  1: "187 条成片 · v3 启用中",
  2: "32 条成片 · v1",
};

const PALETTE = [
  { label: "主色", hex: "#0F2A4A", text: "#F7F9FC" },
  { label: "强调", hex: "#22D3B7", text: "#06101F" },
  { label: "石墨", hex: "#11161F", text: "#F7F9FC" },
  { label: "灰白", hex: "#F7F9FC", text: "#0F2A4A" },
  { label: "信息", hex: "#38BDF8", text: "#06101F" },
  { label: "提示", hex: "#FBBF24", text: "#06101F" },
  { label: "禁止", hex: "#F87171", text: "#06101F" },
  { label: "审核", hex: "#A78BFA", text: "#06101F" },
];

export default async function BrandPage() {
  const { items: kits } = await api.brandKits();

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">品牌套件</span>
        <div className="flex items-end gap-6">
          <div>
            <h1 className="font-display text-[34px] font-semibold tracking-tight">Acme · 核心版</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              每条成片都对照这套渲染。改一次——所有项目重新渲染。偏移会被自动检测，可一键修正。
            </p>
          </div>
          <div className="ml-auto flex gap-3">
            <Button variant="outline">复制</Button>
            <Button variant="outline">导出 ZIP</Button>
            <Button>
              <Check className="h-4 w-4" /> 发布 v4
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[260px_1fr] items-start">
        <div className="grid gap-3">
          {kits.map((k, i) => {
            const active = i === 0;
            return (
              <Card
                key={k.id}
                className={`cursor-pointer p-3 transition-colors ${
                  active ? "border-accent-500/40 bg-accent-500/[0.06]" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    aria-hidden
                    className="h-9 w-9 rounded-md border border-border"
                    style={{ background: `linear-gradient(135deg,${k.primary_color},${k.accent_color})` }}
                  />
                  <div className="leading-tight">
                    <b className="text-sm">{k.name}</b>
                    <span className="block text-[11px] text-muted-foreground">
                      {KIT_META[k.id] ?? `${k.tone.voice_profile.slice(0, 10)}…`}
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}
          <Button variant="outline">
            <Plus className="h-4 w-4" /> 新建套件
          </Button>
        </div>

        <div className="grid gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>调色板</CardTitle>
              <Badge variant="done">WCAG AA 已校验</Badge>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {PALETTE.map((p) => (
                  <div
                    key={p.label}
                    className="grid h-[92px] content-end rounded-md border border-border p-4"
                    style={{ background: p.hex, color: p.text }}
                  >
                    <b className="font-display text-sm font-semibold">{p.label}</b>
                    <span className="font-mono text-[11px] opacity-80">{p.hex}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>排版</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="rounded-md border border-border bg-card/50 p-4">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Display · Inter Display 600</span>
                <div className="mt-2 font-display text-4xl font-semibold tracking-tight">像做产品一样交付视频。</div>
                <div className="mt-2 font-display text-xl font-semibold">副标 — Inter Display 600 · 24 / 32</div>
              </div>
              <div className="rounded-md border border-border bg-card/50 p-4">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Body · Inter 400</span>
                <p className="mt-2 max-w-prose text-sm text-muted-foreground">
                  ShadowBlade 把这里发布的品牌套件应用到每一个场景。改一个 token，整批成片按计划重新渲染。
                </p>
                <code className="mt-2 block font-mono text-xs text-accent-300">
                  $ shadowblade render --kit acme-core --project wearable-hub
                </code>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>语态 · 该做 / 不该做</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-w-prose text-sm text-muted-foreground">
                自信、平实、不夸张。先讲客户得到了什么。屏幕上每句话不超过 14 字。
              </div>
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2 rounded-md border border-border bg-card/50 p-4">
                  <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-accent-300">该做</h4>
                  <ul className="list-disc pl-5 text-sm text-muted-foreground">
                    <li>先讲客户得到了什么</li>
                    <li>用单音节动词</li>
                    <li>屏幕上每句话不超过 14 字</li>
                    <li>结尾一句明确的行动号召</li>
                  </ul>
                </div>
                <div className="grid gap-2 rounded-md border border-border bg-card/50 p-4">
                  <h4 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-amber-300">不要</h4>
                  <ul className="list-disc pl-5 text-sm text-muted-foreground">
                    <li>行业黑话（赋能、抓手、闭环）</li>
                    <li>陈词滥调（旅程、阶梯、北极星）</li>
                    <li>感叹号</li>
                    <li>连续超过两个形容词</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  );
}
