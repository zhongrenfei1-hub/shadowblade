import { ApiKeysButton } from "@/components/workspace/api-keys-panel";
import { StudioModeSwitch } from "@/components/workspace/studio-mode-switch";

export default function StudioPage() {
  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">
          Studio · 端到端 AI 视频流水线
        </span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[26px] font-semibold tracking-tight md:text-[34px]">
              一句主题，直接出片。
            </h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              输入「春季美容补水套餐」这样一句话 — 后端跑脚本生成 →
              <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 text-[12px]">edge-tts</code> 配音 →
              <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 text-[12px]">faster-whisper</code> 字幕 →
              智能混剪 → 品牌封面，10–20 秒拿到能直接发抖音/小红书的 MP4。
            </p>
          </div>
          <ApiKeysButton />
        </div>
      </section>

      <StudioModeSwitch />
    </>
  );
}
