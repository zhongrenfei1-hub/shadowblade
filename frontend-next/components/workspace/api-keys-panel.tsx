"use client";

import { useEffect, useState } from "react";
import {
  KeyRound,
  Loader2,
  X,
  Check,
  AlertTriangle,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type KeyRow = {
  slug: string;
  label: string;
  env: string;
  hint: string;
  configured: boolean;
  source: "store" | "env" | null;
  masked: string;
};

const BASE = "/api/v1";

export function ApiKeysButton() {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<KeyRow[]>([]);

  // Pre-load on mount so the button can show a badge with count of configured keys.
  useEffect(() => {
    if (!open) return;
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function load() {
    try {
      const r = await fetch(`${BASE}/keys`, { cache: "no-store" });
      const data = await r.json();
      setRows(data.items ?? []);
    } catch {
      setRows([]);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.02] px-2.5 py-1.5 text-xs text-muted-foreground hover:border-white/20 hover:text-foreground"
        title="管理 API keys"
      >
        <KeyRound size={12} />
        API keys
      </button>

      {open && (
        <Modal onClose={() => setOpen(false)}>
          <KeysList rows={rows} reload={load} onClose={() => setOpen(false)} />
        </Modal>
      )}
    </>
  );
}

function Modal({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 backdrop-blur-sm p-4 pt-[8vh]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-lg border border-white/10 bg-[#0c1018] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <KeyRound size={14} className="text-accent-300" />
            管理 API keys
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-muted-foreground hover:bg-white/5 hover:text-foreground"
          >
            <X size={14} />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

function KeysList({
  rows,
  reload,
  onClose,
}: {
  rows: KeyRow[];
  reload: () => Promise<void>;
  onClose: () => void;
}) {
  if (!rows.length) {
    return (
      <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
        <Loader2 size={14} className="animate-spin" /> 加载中…
      </div>
    );
  }
  return (
    <div className="grid gap-3">
      <p className="text-xs text-muted-foreground">
        持久化到 <code className="rounded bg-white/5 px-1">~/.shadowblade/secrets.json</code>{" "}
        （仅本机 600 权限）· 修改立即生效，无需重启后端
      </p>
      {rows.map((r) => (
        <KeyRowEditor key={r.slug} row={r} reload={reload} />
      ))}
    </div>
  );
}

function KeyRowEditor({ row, reload }: { row: KeyRow; reload: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; reason: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!value.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${BASE}/keys`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ slug: row.slug, value: value.trim() }),
      });
      if (!r.ok) throw new Error(await r.text());
      setEditing(false);
      setValue("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`删除 ${row.label} 的 key？`)) return;
    setBusy(true);
    try {
      await fetch(`${BASE}/keys/${row.slug}`, { method: "DELETE" });
      await reload();
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setBusy(true);
    setTestResult(null);
    try {
      const r = await fetch(`${BASE}/keys/${row.slug}/test`, { method: "POST" });
      const data = await r.json();
      setTestResult({ ok: data.ok, reason: data.reason });
    } catch (err) {
      setTestResult({ ok: false, reason: err instanceof Error ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }

  const hintUrl = extractUrl(row.hint);

  return (
    <div className="rounded-md border border-white/10 bg-white/[0.02] p-3">
      <div className="flex items-start gap-3">
        <div className="grid flex-1 gap-0.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{row.label}</span>
            {row.configured ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300">
                <Check size={9} /> 已配置
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-muted-foreground">
                未配置
              </span>
            )}
            {row.source === "env" && (
              <span className="text-[10px] text-amber-300/80" title="来自环境变量，不能从这里覆盖">
                env
              </span>
            )}
          </div>
          <p className="text-[11px] text-muted-foreground">
            <code className="rounded bg-white/5 px-1">{row.env}</code> · {plainHint(row.hint)}{" "}
            {hintUrl && (
              <a
                href={hintUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-0.5 text-accent-300 hover:underline"
              >
                申请 <ExternalLink size={9} />
              </a>
            )}
          </p>
          {row.configured && row.masked && (
            <p className="text-[11px] font-mono text-muted-foreground">{row.masked}</p>
          )}
        </div>
        <div className="flex shrink-0 gap-1">
          {row.configured && (
            <>
              <Button variant="ghost" size="sm" onClick={test} disabled={busy} title="测试连通性">
                {busy ? <Loader2 size={12} className="animate-spin" /> : "测试"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={remove}
                disabled={busy}
                title="删除"
              >
                <Trash2 size={12} />
              </Button>
            </>
          )}
          <Button
            variant={editing ? "ghost" : "outline"}
            size="sm"
            onClick={() => setEditing(!editing)}
          >
            {editing ? "取消" : row.configured ? "更新" : "添加"}
          </Button>
        </div>
      </div>

      {editing && (
        <div className="mt-3 flex gap-2">
          <Input
            type="password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={`粘贴 ${row.label} key`}
            className="flex-1 font-mono text-xs"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && save()}
          />
          <Button onClick={save} disabled={busy || !value.trim()}>
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
            保存
          </Button>
        </div>
      )}

      {error && (
        <div className="mt-2 flex items-start gap-1.5 rounded border border-destructive/40 bg-destructive/10 p-2 text-[11px] text-destructive">
          <AlertTriangle size={11} className="mt-0.5 shrink-0" />
          <span className="break-all">{error}</span>
        </div>
      )}

      {testResult && (
        <div
          className={cn(
            "mt-2 flex items-start gap-1.5 rounded border p-2 text-[11px]",
            testResult.ok
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
              : "border-amber-400/40 bg-amber-400/10 text-amber-200",
          )}
        >
          {testResult.ok ? (
            <Check size={11} className="mt-0.5 shrink-0" />
          ) : (
            <AlertTriangle size={11} className="mt-0.5 shrink-0" />
          )}
          <span>{testResult.reason}</span>
        </div>
      )}
    </div>
  );
}

function extractUrl(hint: string): string | null {
  const m = hint.match(/https?:\/\/\S+/);
  return m ? m[0] : null;
}

function plainHint(hint: string): string {
  return hint.replace(/https?:\/\/\S+/g, "").trim();
}
