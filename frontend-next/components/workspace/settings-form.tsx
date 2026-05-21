"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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

export function SettingsForm() {
  const [previewLinks, setPreviewLinks] = useState(true);
  const [autoRender, setAutoRender] = useState(true);
  const [watermark, setWatermark] = useState(false);
  const [mfa, setMfa] = useState(true);

  return (
    <div className="grid gap-4">
      <Card id="general">
        <CardHeader>
          <CardTitle>通用</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid grid-cols-1 items-start gap-3 border-b border-border pb-4 sm:grid-cols-[1fr_260px] sm:items-center sm:gap-4">
            <div>
              <div className="text-sm font-semibold">工作空间名称</div>
              <div className="mt-0.5 text-xs text-muted-foreground">显示在侧边栏和每一次导出里。</div>
            </div>
            <Input defaultValue="Acme Marketing Cloud" />
          </div>
          <div className="grid grid-cols-1 items-start gap-3 border-b border-border pb-4 sm:grid-cols-[1fr_260px] sm:items-center sm:gap-4">
            <div>
              <div className="text-sm font-semibold">区域</div>
              <div className="mt-0.5 text-xs text-muted-foreground">所有素材和渲染都留在此区域。</div>
            </div>
            <select aria-label="区域" className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm">
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
          <div className="grid grid-cols-1 items-start gap-3 border-b border-border pb-4 sm:grid-cols-[1fr_220px] sm:items-center sm:gap-4">
            <div>
              <div className="text-sm font-semibold">默认编码</div>
              <div className="mt-0.5 text-xs text-muted-foreground">H.264 覆盖所有消费端；H.265 用于广播。</div>
            </div>
            <select aria-label="默认编码" className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm">
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
          <div className="grid grid-cols-1 items-start gap-3 sm:grid-cols-[1fr_220px] sm:items-center sm:gap-4">
            <div>
              <div className="text-sm font-semibold">会话时长</div>
              <div className="mt-0.5 text-xs text-muted-foreground">闲置后自动登出。</div>
            </div>
            <select aria-label="会话时长" className="h-10 rounded-md border border-input bg-card/60 px-3 text-sm">
              <option>12 小时</option>
              <option>8 小时</option>
              <option>4 小时</option>
              <option>1 小时</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card id="billing">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>套餐与计费</CardTitle>
          <Badge variant="default">规模版 · 月付</Badge>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid grid-cols-[1fr_auto] items-center gap-4 border-b border-border pb-4">
            <div>
              <div className="text-sm font-semibold">本月用量</div>
              <div className="mt-0.5 text-xs text-muted-foreground">387 / 1,000 条渲染 · 周期重置 5 月 31 日。</div>
            </div>
            <span className="font-mono text-sm text-accent-300 num">38.7%</span>
          </div>
          <div className="grid grid-cols-[1fr_auto] items-center gap-4">
            <div>
              <div className="text-sm font-semibold">支付方式</div>
              <div className="mt-0.5 text-xs text-muted-foreground">Visa ···· 4242 · 6 月到期</div>
            </div>
            <Button size="sm" variant="outline">管理</Button>
          </div>
        </CardContent>
      </Card>

      <Card id="integrations">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>集成快捷入口</CardTitle>
          <Button size="sm" variant="outline" asChild>
            <a href="/integrations">查看全部</a>
          </Button>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          已连接 Slack · Figma · Okta · Notion。改动会同步到工作空间所有成员，权限由角色控制。
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
              {"\n  "}<span className="text-amber-300">&quot;template&quot;</span>:  <span className="text-accent-300">&quot;hero-launch&quot;</span>,
              {"\n  "}<span className="text-amber-300">&quot;brand_kit&quot;</span>: <span className="text-accent-300">&quot;acme-core&quot;</span>,
              {"\n  "}<span className="text-amber-300">&quot;brief&quot;</span>:     <span className="text-accent-300">&quot;春季产品发布 — 智能腕环&quot;</span>,
              {"\n  "}<span className="text-amber-300">&quot;webhook&quot;</span>:   <span className="text-accent-300">&quot;https://acme.example.com/hooks/sb&quot;</span>
              {"\n}"}
            </code>
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
