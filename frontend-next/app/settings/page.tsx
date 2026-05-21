"use client";

import { useState } from "react";
import { Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={cn(
        "relative h-[22px] w-[38px] rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        on ? "bg-accent-500" : "bg-secondary"
      )}
    >
      <span
        className={cn(
          "absolute top-[3px] block h-4 w-4 rounded-full transition-all",
          on ? "left-[19px] bg-navy-900" : "left-[3px] bg-foreground"
        )}
      />
    </button>
  );
}

const SECTIONS = [
  { id: "general", label: "通用" },
  { id: "render", label: "渲染与画质" },
  { id: "security", label: "安全与 SSO" },
  { id: "billing", label: "套餐与计费" },
  { id: "integrations", label: "集成" },
  { id: "api", label: "API 与 Webhook" },
];

export default function SettingsPage() {
  const [previewLinks, setPreviewLinks] = useState(true);
  const [autoRender, setAutoRender] = useState(true);
  const [watermark, setWatermark] = useState(false);
  const [mfa, setMfa] = useState(true);

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">工作空间设置</span>
        <div className="flex items-end gap-6">
          <div>
            <h1 className="font-display text-[34px] font-semibold tracking-tight">设置</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              流水线、安全、计费、集成。改动作用于整个工作空间，并写入审计日志。
            </p>
          </div>
          <div className="ml-auto flex gap-3">
            <Button variant="outline">
              <X className="h-4 w-4" /> 取消
            </Button>
            <Button>
              <Save className="h-4 w-4" /> 保存
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-[220px_1fr] gap-6 items-start">
        <nav className="sticky top-[76px] grid gap-1">
          {SECTIONS.map((s, i) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className={`rounded-md px-3 py-2 text-sm transition-colors ${
                i === 0 ? "bg-accent-500/12 text-foreground" : "text-muted-foreground hover:bg-white/[0.04]"
              }`}
            >
              {s.label}
            </a>
          ))}
        </nav>

        <div className="grid gap-4">
          <Card id="general">
            <CardHeader>
              <CardTitle>通用</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid grid-cols-[1fr_260px] items-center gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-sm font-semibold">工作空间名称</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">显示在侧边栏和每一次导出里。</div>
                </div>
                <Input defaultValue="Acme Marketing Cloud" />
              </div>
              <div className="grid grid-cols-[1fr_260px] items-center gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-sm font-semibold">区域</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">所有素材和渲染都留在此区域。</div>
                </div>
                <select className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm">
                  <option>eu-central-1 · 法兰克福</option>
                  <option>us-east-1 · 弗吉尼亚</option>
                  <option>ap-east-1 · 香港</option>
                </select>
              </div>
              <div className="grid grid-cols-[1fr_auto] items-center gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-sm font-semibold">公开预览链接</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">允许没有席位的审核员通过签名链接观看未完成的成片。</div>
                </div>
                <Toggle on={previewLinks} onChange={setPreviewLinks} label="公开预览链接" />
              </div>
            </CardContent>
          </Card>

          <Card id="render">
            <CardHeader>
              <CardTitle>渲染与画质</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid grid-cols-[1fr_220px] items-center gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-sm font-semibold">默认编码</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">H.264 覆盖所有消费端；H.265 用于广播。</div>
                </div>
                <select className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm">
                  <option>H.264（推荐）</option>
                  <option>H.265 / HEVC</option>
                  <option>ProRes 422 HQ</option>
                </select>
              </div>
              <div className="grid grid-cols-[1fr_auto] items-center gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-sm font-semibold">审批通过自动渲染</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">最后一位审核员批准时立即输出 MP4。</div>
                </div>
                <Toggle on={autoRender} onChange={setAutoRender} label="审批通过自动渲染" />
              </div>
              <div className="grid grid-cols-[1fr_auto] items-center gap-4">
                <div>
                  <div className="text-sm font-semibold">草稿打水印</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">外部分享的未发布成片自动加 "DRAFT" 浅水印。</div>
                </div>
                <Toggle on={watermark} onChange={setWatermark} label="草稿打水印" />
              </div>
            </CardContent>
          </Card>

          <Card id="security">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>安全与 SSO</CardTitle>
              <Badge variant="done">SOC 2 Type II</Badge>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid grid-cols-[1fr_auto] items-center gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-sm font-semibold">SSO 提供商</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">SAML 2.0 · 工作空间强制开启。</div>
                </div>
                <Badge variant="default">Okta · 已连接</Badge>
              </div>
              <div className="grid grid-cols-[1fr_auto] items-center gap-4 border-b border-border pb-4">
                <div>
                  <div className="text-sm font-semibold">强制 MFA</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">WebAuthn 或 TOTP · 适用全员。</div>
                </div>
                <Toggle on={mfa} onChange={setMfa} label="强制 MFA" />
              </div>
              <div className="grid grid-cols-[1fr_220px] items-center gap-4">
                <div>
                  <div className="text-sm font-semibold">会话时长</div>
                  <div className="mt-0.5 text-xs text-muted-foreground">闲置后自动登出。</div>
                </div>
                <select className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm">
                  <option>12 小时</option>
                  <option>8 小时</option>
                  <option>4 小时</option>
                  <option>1 小时</option>
                </select>
              </div>
            </CardContent>
          </Card>

          <Card id="api">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>API 与 Webhook</CardTitle>
              <Button size="sm" variant="outline">新建 Token</Button>
            </CardHeader>
            <CardContent className="grid gap-3">
              <div className="text-sm text-muted-foreground">在 CI 中触发渲染 · 完成后回调到你的 webhook。</div>
              <pre className="overflow-x-auto rounded-md border border-border bg-card/70 p-4 font-mono text-xs">
                <code>
                  <span className="text-accent-300">POST</span> https://api.shadowblade.io/v1/projects/101/render{"\n"}
                  Authorization: Bearer <span className="text-accent-300">sk_live_•••••••••••••••••</span>{"\n"}
                  Content-Type: application/json{"\n\n"}
                  {`{`}
                  {"\n  "}<span className="text-amber-300">"template"</span>:  <span className="text-accent-300">"hero-launch"</span>,
                  {"\n  "}<span className="text-amber-300">"brand_kit"</span>: <span className="text-accent-300">"acme-core"</span>,
                  {"\n  "}<span className="text-amber-300">"brief"</span>:     <span className="text-accent-300">"春季产品发布 — 智能腕环"</span>,
                  {"\n  "}<span className="text-amber-300">"webhook"</span>:   <span className="text-accent-300">"https://acme.example.com/hooks/sb"</span>
                  {"\n}"}
                </code>
              </pre>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  );
}
