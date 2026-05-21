"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[app error]", error);
  }, [error]);

  return (
    <div className="grid min-h-[60vh] place-items-center">
      <div className="grid max-w-md gap-4 text-center">
        <div className="grid place-items-center">
          <span className="grid h-12 w-12 place-items-center rounded-full bg-amber-500/15 text-amber-300">
            <AlertTriangle className="h-6 w-6" aria-hidden />
          </span>
        </div>
        <h1 className="font-display text-2xl font-semibold">服务器临时异常</h1>
        <p className="text-sm text-muted-foreground">
          页面没能渲染出来。重试一次，多半就好；如果还是失败，请联系工作空间管理员。
        </p>
        {error.digest && (
          <p className="font-mono text-[11px] text-muted-foreground">事件 ID：{error.digest}</p>
        )}
        <div className="grid place-items-center">
          <Button onClick={reset}>
            <RefreshCw className="h-4 w-4" /> 重试
          </Button>
        </div>
      </div>
    </div>
  );
}
