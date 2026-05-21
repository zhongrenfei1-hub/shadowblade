/**
 * (app) 路由组的 loading boundary。
 *
 * 沿用应用工作台骨架：hero + 4 列 KPI + 双栏。给已登录员工看的形状。
 * 外部访客走 `(external)/loading.tsx`，形状轻量。
 */
export default function AppLoading() {
  return (
    <div className="grid gap-6 animate-fade-up" aria-busy="true" aria-label="正在加载工作台">
      <div className="grid gap-3">
        <div className="skel h-3 w-32 rounded" />
        <div className="skel h-9 w-72 rounded" />
        <div className="skel h-4 w-96 max-w-full rounded" />
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="grid gap-3 rounded-xl border border-border/85 bg-card/60 p-5"
          >
            <div className="skel h-3 w-24 rounded" />
            <div className="skel h-10 w-32 rounded" />
            <div className="skel h-4 w-20 rounded-full" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="grid gap-3 rounded-xl border border-border/85 bg-card/60 p-6">
          <div className="skel h-5 w-48 rounded" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-md border border-border bg-card/40 p-4">
              <div className="skel h-6 w-6 rounded-md" />
              <div className="flex-1 space-y-1.5">
                <div className="skel h-3 w-32 rounded" />
                <div className="skel h-3 w-56 max-w-full rounded" />
              </div>
              <div className="skel h-3 w-12 rounded" />
            </div>
          ))}
        </div>
        <div className="grid gap-3 rounded-xl border border-border/85 bg-card/60 p-6">
          <div className="skel h-5 w-32 rounded" />
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-md border border-border bg-card/40 p-4">
              <div className="skel h-6 w-6 rounded" />
              <div className="flex-1 space-y-1.5">
                <div className="skel h-3 w-40 max-w-full rounded" />
                <div className="skel h-3 w-32 max-w-full rounded" />
              </div>
              <div className="skel h-7 w-12 rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
