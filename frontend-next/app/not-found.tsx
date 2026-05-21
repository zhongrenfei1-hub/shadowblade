import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * 根 not-found · 不知道访客身份的 fallback。
 *
 * 已登录员工的 404 由 `(app)/not-found.tsx` 接管（CTA 直跳工作台 / 项目库）；
 * 外部访客的失效分享链接由 `(external)/not-found.tsx` 接管（无内链 + 「请联系分享者」）。
 *
 * 这里只给单 CTA「回到首页」——次按钮「进入工作台」之前有 friction：
 * demo 阶段无 middleware，未登录访客点了会进 (app)/layout 看到 mock 工作空间数据。
 * 等 design v5 加 middleware（未登录 → /login）后再视情况补回。
 */
export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center px-4 text-center">
      <div className="grid max-w-md gap-4">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-amber-500/15 text-amber-300">
          <FileQuestion className="h-6 w-6" aria-hidden />
        </span>
        <h1 className="font-display text-2xl font-semibold">这个页面没有渲染出来</h1>
        <p className="text-sm text-muted-foreground">
          你点击的链接可能已失效。回到首页看看其他入口。
        </p>
        <div className="flex justify-center">
          <Button asChild>
            <Link href="/">回到首页</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
