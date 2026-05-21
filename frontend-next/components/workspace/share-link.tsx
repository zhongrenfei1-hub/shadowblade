"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ShareLink({ url }: { url: string }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  async function copyShare() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setCopied(false), 1800);
    } catch {
      // 浏览器不支持 clipboard API 时静默失败。
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Input value={url} readOnly className="font-mono text-xs" />
      <Button variant="outline" onClick={copyShare}>
        {copied ? <Check className="h-4 w-4 text-accent-300" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
        {copied ? "已复制" : "复制"}
      </Button>
    </div>
  );
}
