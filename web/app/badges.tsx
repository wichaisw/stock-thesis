import type { CdcState } from "@/lib/engine";

const STATE_STYLE: Record<CdcState, string> = {
  "just-crossed": "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  "bear-approaching": "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  "bear-far": "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  bull: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
};

export function StateBadge({ state }: { state: CdcState | null }) {
  if (!state) return <span className="text-zinc-500">N/A</span>;
  return <span className={`rounded px-2 py-0.5 text-xs font-medium whitespace-nowrap ${STATE_STYLE[state]}`}>{state}</span>;
}

export function Tag({ children, tone = "zinc", title }: { children: React.ReactNode; tone?: "red" | "violet" | "zinc"; title?: string }) {
  const style = {
    red: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    violet: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300",
    zinc: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  }[tone];
  return (
    <span title={title} className={`rounded px-2 py-0.5 text-xs font-medium ${style}`}>
      {children}
    </span>
  );
}

export function Info({ text }: { text: string }) {
  return (
    <span role="img" title={text} aria-label={text} className="ml-1 cursor-help text-zinc-400">
      ⓘ
    </span>
  );
}

/** Hover shows the reason; aria-label carries it for screen readers. */
export function FailIcon({ reason }: { reason: string }) {
  return (
    <span role="img" title={reason} aria-label={`ดึงข้อมูลไม่ได้: ${reason}`} className="cursor-help text-amber-600">
      ⚠
    </span>
  );
}
