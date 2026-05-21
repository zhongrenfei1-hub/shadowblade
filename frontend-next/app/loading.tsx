import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="grid min-h-[60vh] place-items-center">
      <div className="grid place-items-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-accent-300" aria-hidden />
        <p className="text-sm text-muted-foreground">载入中…</p>
      </div>
    </div>
  );
}
