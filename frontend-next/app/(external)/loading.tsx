/**
 * (external) 路由组的 loading boundary。
 *
 * 外部访客（分享链接、未来 /login / /status）走的不是 app 工作台骨架，
 * 应单独给一份「中央居中、轻量」的占位，而不是借用根 loading 的 KPI 4 列。
 */
export default function ExternalLoading() {
  return (
    <div className="grid min-h-screen place-items-center px-4" aria-busy="true" aria-label="正在加载分享内容">
      <div className="grid w-full max-w-md gap-4">
        <div className="skel mx-auto h-7 w-40 rounded" />
        <div className="skel h-48 w-full rounded-lg" />
        <div className="grid gap-2">
          <div className="skel h-3 w-3/4 rounded" />
          <div className="skel h-3 w-1/2 rounded" />
        </div>
      </div>
    </div>
  );
}
