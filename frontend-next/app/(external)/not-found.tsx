import { Link2Off } from "lucide-react";

/**
 * (external) 路由组的 404。
 *
 * 外部访客没有 ShadowBlade 账号，看不到「返回工作台 / 项目库」的入口，
 * 单独给一份「链接失效」语义的极简页面（不需要 EmptyState 那么重）。
 */
export default function ExternalNotFound() {
  return (
    <div className="grid min-h-screen place-items-center px-4 text-center">
      <div className="grid max-w-md gap-4">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-amber-500/15 text-amber-300">
          <Link2Off className="h-6 w-6" aria-hidden />
        </span>
        <h1 className="font-display text-2xl font-semibold">这个分享链接不存在</h1>
        <p className="text-sm text-muted-foreground">
          链接可能已被作者撤回，或者已过期。请联系分享者重发一个新链接。
        </p>
      </div>
    </div>
  );
}
