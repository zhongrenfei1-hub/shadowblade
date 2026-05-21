import { StudioWorkbench } from "@/components/workspace/studio-workbench";

export default function StudioPage() {
  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          Studio · 真混剪流水线
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[26px] font-semibold tracking-tight md:text-[34px]">
              连上 ffmpeg，直接渲染。
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              通过 <code className="rounded bg-white/5 px-1.5 py-0.5 text-[12px]">/api/v1/mix-video</code>{" "}
              触发后端真实流水线 — 智能过渡、人声+BGM ducking、品牌字幕、水印、封面，输出可播放的 MP4。
            </p>
          </div>
        </div>
      </section>

      <StudioWorkbench />
    </>
  );
}
