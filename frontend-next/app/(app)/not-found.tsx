import { FileQuestion } from "lucide-react";
import { EmptyState } from "@/components/marketing/empty-state";

/**
 * (app) 路由组的 404。
 *
 * 已登录员工看到 — CTA 跳工作台 / 项目库。
 * 外部访客的 404 在 `(external)/not-found.tsx`。
 */
export default function AppNotFound() {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <EmptyState
        icon={FileQuestion}
        title="这个页面没有渲染出来"
        description="你点击的链接可能已失效，或者项目已归档。回到工作台试试。"
        action={{ label: "返回工作台", href: "/dashboard" }}
        secondaryAction={{ label: "项目库", href: "/projects", variant: "outline" }}
      />
    </div>
  );
}
