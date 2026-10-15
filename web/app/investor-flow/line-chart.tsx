"use client";

import { type KeyboardEvent, type ReactNode, useState } from "react";

import { INVESTOR_TYPES, type InvestorType } from "@/lib/engine";

export type ChartPoint = { label: string; values: Record<InvestorType, number> };

// dataviz reference palette slots 1-4 (light / dark steps); fixed per type so hiding a line never repaints the others
const COLOR: Record<InvestorType, { stroke: string; bg: string }> = {
  institution: { stroke: "stroke-[#2a78d6] dark:stroke-[#3987e5]", bg: "bg-[#2a78d6] dark:bg-[#3987e5]" },
  proprietary: { stroke: "stroke-[#eb6834] dark:stroke-[#d95926]", bg: "bg-[#eb6834] dark:bg-[#d95926]" },
  foreign: { stroke: "stroke-[#1baf7a] dark:stroke-[#199e70]", bg: "bg-[#1baf7a] dark:bg-[#199e70]" },
  individual: { stroke: "stroke-[#eda100] dark:stroke-[#c98500]", bg: "bg-[#eda100] dark:bg-[#c98500]" },
};

const W = 720;
const H = 300;
const PAD = { top: 12, right: 16, bottom: 28, left: 72 };
// about 7 x-axis labels keeps them apart when the chart shrinks on a phone
const X_LABELS = 7;

function million(x: number): string {
  const s = Math.round(x / 1e6).toLocaleString("th-TH");
  return x > 0 ? `+${s}` : s;
}

/** Round step (1, 2 or 5 × 10^n) giving about 5 gridlines; always includes 0. */
function yTicks(min: number, max: number): number[] {
  const raw = (max - min) / 5 || 1;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const ticks = [];
  for (let v = Math.floor(min / step) * step; v <= max + step / 2; v += step) ticks.push(v);
  return ticks;
}

/** Net value lines of the 4 investor types, in baht; toggles per type and a readout for hover or arrow keys. */
export function NetLineChart({
  title,
  ariaLabel,
  points,
  labels,
  caption,
}: {
  title: string;
  ariaLabel: string;
  points: ChartPoint[];
  labels: Record<InvestorType, string>;
  caption: ReactNode;
}) {
  const [hidden, setHidden] = useState<Set<InvestorType>>(new Set());
  const [active, setActive] = useState<number | null>(null);
  const shown = INVESTOR_TYPES.filter((t) => !hidden.has(t));
  const last = points.length - 1;

  const values = shown.flatMap((t) => points.map((p) => p.values[t]));
  const ticks = yTicks(Math.min(0, ...values), Math.max(0, ...values));
  const [lo, hi] = [ticks[0], ticks[ticks.length - 1]];
  const band = (W - PAD.left - PAD.right) / Math.max(last, 1);
  const x = (i: number) => PAD.left + i * band;
  const y = (v: number) => PAD.top + ((hi - v) * (H - PAD.top - PAD.bottom)) / (hi - lo || 1);
  const labelStep = Math.max(1, Math.ceil(points.length / X_LABELS));
  const current = points[active ?? last];

  const toggle = (t: InvestorType) =>
    setHidden((h) => {
      const next = new Set(h);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });

  const onKey = (e: KeyboardEvent) => {
    const at = active ?? last;
    const next = { ArrowLeft: at - 1, ArrowRight: at + 1, Home: 0, End: last }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    setActive(Math.min(Math.max(next, 0), last));
  };

  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="flex flex-wrap gap-2 text-sm">
        {INVESTOR_TYPES.map((t) => (
          <button
            key={t}
            type="button"
            aria-pressed={!hidden.has(t)}
            onClick={() => toggle(t)}
            className="flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-1 aria-[pressed=false]:text-zinc-400 aria-[pressed=false]:line-through dark:border-zinc-700"
          >
            <span aria-hidden className={`h-0.5 w-4 rounded ${COLOR[t].bg} ${hidden.has(t) ? "opacity-30" : ""}`} />
            {labels[t]}
          </button>
        ))}
      </div>

      <div aria-live="polite" className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        <span className="font-medium">{current.label}</span>
        {shown.map((t) => (
          <span key={t} className="text-zinc-600 dark:text-zinc-400">
            {labels[t]} <span className="font-medium text-zinc-900 dark:text-zinc-100">{million(current.values[t])}</span>
          </span>
        ))}
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full rounded-md border border-zinc-200 text-zinc-500 outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-800"
        role="group"
        tabIndex={0}
        aria-label={`${ariaLabel} หน่วยล้านบาท ใช้ลูกศรซ้ายขวาเพื่ออ่านค่าแต่ละจุด`}
        onKeyDown={onKey}
        onMouseLeave={() => setActive(null)}
        onBlur={() => setActive(null)}
      >
        {ticks.map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(v)}
              y2={y(v)}
              className={v === 0 ? "stroke-zinc-400 dark:stroke-zinc-500" : "stroke-zinc-200 dark:stroke-zinc-800"}
            />
            <text x={PAD.left - 8} y={y(v)} textAnchor="end" dominantBaseline="middle" className="fill-current text-[11px]">
              {Math.round(v / 1e6).toLocaleString("th-TH")}
            </text>
          </g>
        ))}
        {points.map((p, i) =>
          i === last || (i % labelStep === 0 && last - i >= labelStep) ? (
            <text
              key={i}
              x={x(i)}
              y={H - 8}
              textAnchor={i === last ? "end" : "middle"}
              className="fill-current text-[11px]"
            >
              {p.label}
            </text>
          ) : null,
        )}
        {active !== null && (
          <line x1={x(active)} x2={x(active)} y1={PAD.top} y2={H - PAD.bottom} className="stroke-zinc-400" strokeDasharray="3 3" />
        )}
        {shown.map((t) => (
          <g key={t} className={COLOR[t].stroke}>
            <polyline
              fill="none"
              strokeWidth={2}
              strokeLinejoin="round"
              points={points.map((p, i) => `${x(i)},${y(p.values[t])}`).join(" ")}
            />
            {active !== null && (
              <circle cx={x(active)} cy={y(points[active].values[t])} r={4} strokeWidth={2} className="fill-white dark:fill-zinc-950" />
            )}
          </g>
        ))}
        {points.map((_, i) => (
          <rect
            key={i}
            x={x(i) - band / 2}
            y={PAD.top}
            width={band}
            height={H - PAD.top - PAD.bottom}
            fill="transparent"
            onMouseEnter={() => setActive(i)}
          />
        ))}
      </svg>

      <p className="text-sm text-zinc-500">{caption}</p>
    </section>
  );
}
