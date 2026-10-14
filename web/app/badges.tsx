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

/**
 * Shows on hover and on keyboard focus, unlike `title`. The text spans the nearest `relative`
 * ancestor rather than hanging off the icon, so it cannot run off a narrow screen.
 */
export function Tooltip({ id, text, label }: { id: string; text: string; label: string }) {
  return (
    <span className="group">
      <button
        type="button"
        aria-label={`คำอธิบาย ${label}`}
        aria-describedby={id}
        className="ml-1 cursor-help rounded text-zinc-400 hover:text-zinc-600 focus-visible:outline-2 focus-visible:outline-zinc-500"
      >
        ⓘ
      </button>
      <span
        id={id}
        role="tooltip"
        className="invisible absolute inset-x-0 top-full z-10 mt-1 rounded-md bg-zinc-900 px-3 py-2 text-xs leading-relaxed font-normal text-white opacity-0 shadow-lg transition-opacity group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {text}
      </span>
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

/** Shown when settings changed after the latest successful run started (its results use the old values). */
export function StaleNotice() {
  return (
    <p role="status" className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
      ผลที่แสดงยังใช้เกณฑ์ก่อนแก้ กด &ldquo;รัน batch&rdquo; เพื่อประเมินใหม่ด้วยค่าล่าสุด
    </p>
  );
}
