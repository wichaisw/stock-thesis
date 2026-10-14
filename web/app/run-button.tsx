"use client";

import { useEffect, useState, useTransition } from "react";

import { latestRun, refreshPage, startRun } from "@/app/actions";
import type { Run } from "@/lib/engine";
import { thaiDateTime } from "@/lib/format";

const POLL_MS = 3000;

// children (the settings shortcut) sit beside the button, so the status line below can wrap without pushing them apart
export function RunButton({ initial, children }: { initial: Run | null; children?: React.ReactNode }) {
  const [run, setRun] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const running = run?.status === "running";

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(async () => {
      const latest = await latestRun().catch(() => null);
      if (latest && latest.status !== "running") {
        setRun(latest);
        await refreshPage();
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [running]);

  function onClick() {
    startTransition(async () => {
      const result = await startRun();
      setError(result.error);
      setRun(await latestRun().catch(() => run));
    });
  }

  return (
    <div className="flex flex-col items-end gap-1 text-sm">
      <div className="flex items-start gap-2">
        {children}
        <button
          type="button"
          onClick={onClick}
          disabled={running || pending}
          className="rounded-md bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-zinc-400"
        >
          {running ? "กำลังรัน batch…" : "รัน batch"}
        </button>
      </div>
      <p aria-live="polite" className="max-w-md text-right text-zinc-500">
        {running && `เริ่มเมื่อ ${thaiDateTime(run.started_at)} (ราว 1–3 นาที)`}
        {run?.status === "failed" && <span className="text-red-600">รันล่าสุดล้มเหลว: {run.error}</span>}
        {error && <span className="text-red-600">{error}</span>}
      </p>
    </div>
  );
}
