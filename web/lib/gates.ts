import type { Check, Evaluation } from "@/lib/engine";

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
