import type { Check, Evaluation } from "@/lib/engine";
import { pct } from "@/lib/format";

// short names for tables and text; the panel keeps the long labels with formulas
export const METHOD_SHORT: Record<string, string> = {
  pe_median: "PE band",
  pe_minus_1sd: "PE band − 1SD",
  pbv_median: "PBV band",
  dividend_yield_median: "Dividend yield band",
  peer_pe: "Peer PE",
  justified_pbv: "Justified PBV",
};

// "12% (Justified PBV)", or N/A for runs before the gate or with no computable gate method
export function mosGate(ev: Evaluation): string {
  const g = ev.fair_value?.gate;
  if (!g || g.mos === null || g.method === null) return "N/A";
  return `${pct(g.mos, 0)} (${METHOD_SHORT[g.method] ?? g.method})`;
}

// one source of gate rows so the candidate list, detail page and LLM export always count the same
export function gateRows(ev: Evaluation, liquidityThreshold: string): Check[] {
  return [
    {
      name: "liquidity",
      passed: ev.liquidity.passed,
      value: ev.liquidity.value,
      threshold: liquidityThreshold,
      reason: ev.liquidity.reason,
    },
    ...(ev.quality?.checks ?? []),
  ];
}

// skipped checks (passed === null) are not evaluated, so a bank scores out of 4, not 6
export function gateTally(rows: Check[]): { passed: number; evaluated: number; failed: Check[] } {
  const evaluated = rows.filter((c) => c.passed !== null);
  return {
    passed: evaluated.filter((c) => c.passed).length,
    evaluated: evaluated.length,
    failed: evaluated.filter((c) => !c.passed),
  };
}
