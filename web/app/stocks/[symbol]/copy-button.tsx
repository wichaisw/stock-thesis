"use client";

import { useEffect, useState } from "react";

const LABEL = { idle: "คัดลอกให้ LLM", copied: "คัดลอกแล้ว", failed: "คัดลอกไม่สำเร็จ" };

export function CopyButton({ text }: { text: string }) {
  const [status, setStatus] = useState<keyof typeof LABEL>("idle");

  useEffect(() => {
    if (status === "idle") return;
    const t = setTimeout(() => setStatus("idle"), 2000);
    return () => clearTimeout(t);
  }, [status]);

  async function copy() {
    try {
      // Clipboard API needs a secure context; opening the app by LAN IP lands in the catch
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      aria-live="polite"
      className={`rounded-md border px-3 py-1 text-sm font-normal hover:bg-zinc-100 dark:hover:bg-zinc-900 ${
        status === "failed" ? "border-red-400 text-red-600" : "border-zinc-300 dark:border-zinc-700"
      }`}
    >
      {LABEL[status]}
    </button>
  );
}
