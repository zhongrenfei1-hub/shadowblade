import { CreateWizard } from "@/components/workspace/create-wizard";

export default function CreatePage() {
  return (
    <>
      <section className="grid gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent-300">新建视频 · 一键生成</span>
        <div className="flex flex-wrap items-end gap-4 md:gap-6">
          <div className="min-w-0 flex-1">
            <h1 className="font-display text-[26px] font-semibold tracking-tight md:text-[34px]">写一份简报，4 分钟拿到成片。</h1>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">
              脚本 → 配音 → 字幕 → 混剪 → 封面 → 品牌水印，全部按你的品牌套件渲染。
            </p>
          </div>
        </div>
      </section>

      <CreateWizard />
    </>
  );
}
