import { Upload, Video, Image as ImageIcon, Music2, Palette } from "lucide-react";
import { api, type Asset } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatBytes } from "@/lib/utils";
import { LibraryFolders } from "@/components/workspace/library-folders";

const ICONS: Record<Asset["kind"], React.ReactNode> = {
  video: <Video className="h-7 w-7" aria-hidden />,
  image: <ImageIcon className="h-7 w-7" aria-hidden />,
  audio: <Music2 className="h-7 w-7" aria-hidden />,
  font: <span className="font-display text-2xl font-bold" aria-hidden>Aa</span>,
};

// logo 资源跟 backend 一致用 kind=image + slug 前缀，渲染时用 Palette icon。
function iconFor(asset: Asset): React.ReactNode {
  if (asset.slug.startsWith("logo-")) return <Palette className="h-7 w-7" aria-hidden />;
  return ICONS[asset.kind];
}

export default async function LibraryPage() {
  const { items, totals } = await api.assets();
  const totalAll = Object.values(totals).reduce((a, b) => a + b, 0);
  const totalBytes = items.reduce((a, b) => a + b.size_bytes, 0);

  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">素材库</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[28px] font-semibold tracking-tight md:text-[34px]">
              <span className="num">{totalAll}</span> 个素材 · {formatBytes(totalBytes)}
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              品牌已审、版权清楚、按画面内容索引。直接拖文件进来，或一句话让 AI 生成。
            </p>
          </div>
          <Button aria-label="上传素材">
            <Upload className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">上传素材</span><span className="sm:hidden">上传</span>
          </Button>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr] items-start">
        {/* 左侧 · 文件夹 + 标签 + 上传区 */}
        <div className="grid gap-4">
          <LibraryFolders totals={totals} totalAll={totalAll} />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">标签</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-1.5">
              {["已审核", "品牌", "CC-BY", "stock", "spring-2026", "外部"].map((t) => (
                <Badge key={t} variant="default" className="cursor-pointer">{t}</Badge>
              ))}
            </CardContent>
          </Card>

          <div className="grid place-items-center gap-3 rounded-lg border-[1.5px] border-dashed border-accent-500/40 bg-accent-500/[0.05] p-6 text-center">
            <Upload className="h-7 w-7 text-accent-300" aria-hidden />
            <b className="font-display text-sm">拖文件或粘贴 URL</b>
            <span className="text-xs text-muted-foreground">MP4 / MOV / PNG / JPG / MP3 / WAV / OTF · 单个最大 4 GB</span>
            <Button size="sm">浏览</Button>
          </div>
        </div>

        {/* 右侧 · 素材网格 */}
        <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
          {items.map((a) => (
            <Card key={a.id} className="cursor-pointer overflow-hidden transition-all hover:-translate-y-0.5 hover:border-accent-500/40">
              <div className="grid h-[110px] place-items-center bg-gradient-to-br from-navy-700 to-navy-900 text-accent-300">
                {iconFor(a)}
              </div>
              <div className="grid gap-1 p-3">
                <div className="truncate text-sm font-semibold">{a.name}</div>
                <div className="flex justify-between text-[11px] text-muted-foreground">
                  <span>{a.kind}</span>
                  <span className="num">{formatBytes(a.size_bytes)}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>
    </>
  );
}
