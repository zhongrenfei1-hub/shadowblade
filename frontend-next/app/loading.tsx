/**
 * 根级 loading fallback。
 *
 * 路由组 `(app)` 与 `(external)` 各自有自己的 loading boundary（更贴形状）。
 * 这里只服务 `/` 一个路由（marketing hero），给一份极简占位即可。
 */
export default function RootLoading() {
  return (
    <div className="grid min-h-screen place-items-center px-4" aria-busy="true" aria-label="正在加载">
      <div className="grid w-full max-w-xl gap-4">
        <div className="skel h-3 w-32 rounded" />
        <div className="skel h-12 w-3/4 rounded" />
        <div className="skel h-4 w-5/6 rounded" />
        <div className="skel h-4 w-2/3 rounded" />
      </div>
    </div>
  );
}
