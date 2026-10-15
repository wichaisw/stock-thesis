import { describe, expect, test } from "bun:test";

import type { Check, Evaluation } from "@/lib/engine";
import { gateRows, gateTally, mosGate } from "@/lib/gates";

const ok = (name: string): Check => ({ name, passed: true, value: 1, threshold: "", reason: name });

function ev(checks: Check[] | null): Evaluation {
  return {
    liquidity: { passed: checks !== null, value: 1, threshold: 1, reason: "liq" },
    quality: checks && { passed: true, checks, inflection: { flag: false, reason: null } },
  } as Evaluation;
}

describe("gateTally", () => {
  test("a general stock failing D/E scores 5/6 and lists D/E", () => {
    const de: Check = { name: "de", passed: false, value: 2.3, threshold: "≤ 1.5", reason: "D/E 2.30" };
    const t = gateTally(gateRows(ev([ok("min_quarters"), ok("roe"), de, ok("ocf"), ok("no_loss")]), ""));
    expect([t.passed, t.evaluated]).toEqual([5, 6]);
    expect(t.failed.map((c) => c.reason)).toEqual(["D/E 2.30"]);
  });

  test("a bank does not count skipped D/E and OCF", () => {
    const skip = (name: string): Check => ({ ...ok(name), passed: null });
    const t = gateTally(gateRows(ev([ok("min_quarters"), ok("roe"), skip("de"), skip("ocf"), ok("no_loss")]), ""));
    expect([t.passed, t.evaluated]).toEqual([4, 4]);
  });

  test("a stock without statements scores 0/1", () => {
    const t = gateTally(gateRows(ev(null), ""));
    expect([t.passed, t.evaluated]).toEqual([0, 1]);
  });
});

describe("mosGate", () => {
  const withGate = (gate: object | undefined) => ({ fair_value: { gate } }) as unknown as Evaluation;

  test("shows the lower gate method and its name", () => {
    expect(mosGate(withGate({ mos: 0.12, method: "justified_pbv" }))).toBe("+12% (Justified PBV)");
  });

  test("is N/A without a computable gate method or in a run before the gate", () => {
    expect(mosGate(withGate({ mos: null, method: null }))).toBe("N/A");
    expect(mosGate(withGate(undefined))).toBe("N/A");
  });
});
