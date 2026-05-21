import {
  Download,
  Share2,
  Check,
  Archive,
  Sparkles,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { VideoPlayer } from "@/components/workspace/video-player";
import { ShareLink } from "@/components/workspace/share-link";
import { MetaTabs } from "@/components/workspace/meta-tabs";

const SCENES = [
  { i: "01", t: "冷开场", dur: "4.0" },
  { i: "02", t: "产品主视觉", dur: "5.0" },
  { i: "03", t: "屏幕细节", dur: "4.5" },
  { i: "04", t: "生活场景", dur: "5.0" },
  { i: "05", t: "续航 + 轻触", dur: "5.0" },
  { i: "06", t: "行动号召", dur: "4.5" },
];

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const shareUrl = `https://review.shadowblade.io/r/${params.id}/q7M2xs9`;

  return (
    <article>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          项目 #{params.id} · 营销 · 9:16 · 28 秒
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[26px] font-semibold tracking-tight md:text-[34px]">春季产品发布 — 智能腕环</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              v17 / 17 · 4 分钟前由 Ava Chen 渲染 · Acme · 核心品牌套件 · 灵韵女声配音
            </p>
          </div>
          <div className="flex gap-2 md:gap-3">
            <Button variant="outline">
              <Archive className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">归档</span>
            </Button>
            <Button>
              <Check className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">批准并发布</span><span className="sm:hidden">批准</span>
            </Button>
          </div>
        </div>
      </section>

      <section className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr] items-start">
        {/* ── 左：播放器 + 时间线 ─── */}
        <div className="grid gap-6">
          <Card className="overflow-hidden">
            <VideoPlayer />

            <div className="flex flex-wrap items-center gap-3 border-t border-border bg-card/60 px-5 py-3">
              <Button>
                <Download className="h-4 w-4" aria-hidden /> 下载 MP4
              </Button>
              <Button variant="outline">
                <Share2 className="h-4 w-4" aria-hidden /> 分享给审核员
              </Button>
              <Button variant="outline">
                <Globe className="h-4 w-4" aria-hidden /> 翻译成 5 语言
              </Button>
              <Button variant="outline">
                <Sparkles className="h-4 w-4" aria-hidden /> 再渲染一版
              </Button>
              <div className="ml-auto font-mono text-xs text-muted-foreground">
                1080×1920 · H.264 · 60 fps · 8.4 MB
              </div>
            </div>
          </Card>

          {/* 分享链接卡片 */}
          <Card>
            <CardHeader>
              <CardTitle>分享链接</CardTitle>
              <p className="text-sm text-muted-foreground">
                无需 ShadowBlade 账号即可观看 · 链接 3 天后失效 · 每次访问都记录在审计日志。
              </p>
            </CardHeader>
            <CardContent className="grid gap-3">
              <ShareLink url={shareUrl} />
              <div className="grid grid-cols-1 gap-3 text-xs text-muted-foreground sm:grid-cols-3">
                <span>有效期：<b className="text-foreground">2026-05-24</b></span>
                <span>水印：<b className="text-foreground">DRAFT · v17</b></span>
                <span>访问：<b className="text-foreground">2 人 · 0 次下载</b></span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>场景 · 6 个</CardTitle>
              <Button variant="outline" size="sm">在编辑器中打开</Button>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
                {SCENES.map((s) => (
                  <div key={s.i} className="overflow-hidden rounded-md border border-border bg-card/50">
                    <div className="grid h-[70px] place-items-center bg-gradient-to-br from-navy-700 to-navy-900 font-mono text-[10px] text-muted-foreground">
                      {s.i}
                    </div>
                    <div className="grid gap-0.5 p-2">
                      <b className="text-[11px] font-semibold">{s.t}</b>
                      <span className="font-mono text-[10px] text-muted-foreground">{s.dur} 秒</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* ── 右：tabs · 元数据 + 评论 ─ */}
        <div className="grid gap-4">
          <Card>
            <CardContent className="p-4">
              <MetaTabs />
            </CardContent>
          </Card>
        </div>
      </section>
    </article>
  );
}
