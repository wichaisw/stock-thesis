import { describe, expect, test } from "bun:test";

import type { Evaluation, StockDetail } from "@/lib/engine";
import { toLlmMarkdown } from "@/lib/llm-export";

function candidate(): StockDetail {
  const evaluation: Evaluation = {
    symbol: "KLINIQ",
    name: "Kliniq PCL",
    sector: "Health Care Services",
    market: "SET",
    price: 32.75,
    price_date: "2026-10-14",
    candidate_rank: 3,
    liquidity: { passed: true, value: 12008587, threshold: 3000000, reason: "traded value เฉลี่ย 20 วัน 12.0 ลบ./วัน" },
    quality: {
      passed: true,
      checks: [
        { name: "roe", passed: true, value: 0.2355, threshold: "ROE TTM ≥ 10%", reason: "ROE TTM 23.5%" },
        { name: "de", passed: true, value: 0.87, threshold: "≤ 1.5", reason: "D/E 0.87" },
      ],
      inflection: { flag: false, reason: null },
    },
    fair_value: {
      price: 32.75,
      eps_ttm: 1.9206,
      items: [
        { method: "pe_median", label: "PE band (median 5 ปี)", fair_value: 37.35, mos: 0.123, reason: null },
        { method: "dividend_yield_median", label: "Dividend yield band (median 5 ปี)", fair_value: 33.76, mos: 0.03, reason: null },
      ],
      summary: {
        label: "2/2 undervalued",
        undervalued: 2,
        computed: 2,
        min_mos: 0.03,
        median_mos: 0.0765,
        max_mos: 0.123,
        median_fair_value: 35.56,
        max_fair_value: 37.35,
      },
      structure_change: { flag: false, reason: null },
      history_gap: { flag: false, reason: null },
    },
    cdc: { state: "just-crossed", fast: 29.706554, slow: 29.087384, gap_pct: -0.021287, speed: 0.006349, eta_days: null, days_since_cross: 2, reason: null },
    risk_reward: {
      entry: 32.75,
      stop: 27,
      target: 36.35,
      target_optimistic: 40.9,
      rrr: 0.63,
      low_rrr: true,
      upside: 0.1099,
      hold_months: 1.02,
      reward_per_month: 0.1079,
      reason: null,
    },
    inclusion: { included: true, reasons: [] },
  };
  return {
    stock: { symbol: "KLINIQ", name: "Kliniq PCL", sector: "Health Care Services", market: "SET" },
    run: null,
    evaluation,
    failure: null,
    hints: { sector_matched: true, items: ["จำนวนผู้ป่วยต่างชาติ"] },
    events: [{ date: "2026-11-14", label: "กำหนดส่งงบไตรมาส 3/2026", kind: "statement", estimated: true }],
  };
}

function rejected(): StockDetail {
  const d = candidate();
  const ev = d.evaluation!;
  ev.candidate_rank = null;
  ev.inclusion = { included: false, reasons: ["ไม่ผ่าน quality gate", "median margin of safety 7.7% ต่ำกว่าเกณฑ์ 10%"] };
  ev.quality!.passed = false;
  ev.quality!.checks[0] = { name: "roe", passed: false, value: 0.06, threshold: "ROE TTM ≥ 10%", reason: "ROE TTM 6.0% | ต่ำกว่าเกณฑ์" };
  ev.fair_value!.items[1] = {
    method: "dividend_yield_median",
    label: "Dividend yield band (median 5 ปี)",
    fair_value: null,
    mos: null,
    reason: "ไม่ได้จ่ายปันผลเงินสดใน 12 เดือนล่าสุด",
  };
  ev.fair_value!.structure_change = { flag: true, reason: "ส่วนผู้ถือหุ้น +69% ใน 2023Q2" };
  return d;
}

function failed(): StockDetail {
  return {
    stock: { symbol: "GSTEEL", name: "G Steel PCL", sector: "Steel", market: "SET" },
    run: null,
    evaluation: null,
    failure: "No data found",
    hints: { sector_matched: false, items: ["ข่าวลงทุนหรือ M&A"] },
    events: [],
  };
}

const SECTIONS = ["Candidate status", "Gates", "Fair value", "CDC", "Risk / reward", "Catalyst hints", "Events", "Method notes"];

describe("toLlmMarkdown", () => {
  test("starts with a prompt asking for a Thai second opinion before the data", () => {
    const md = toLlmMarkdown(candidate());
    const prompt = md.slice(0, md.indexOf("# KLINIQ"));
    expect(prompt).toContain("second opinion");
    expect(prompt).toContain("Thai");
    expect(prompt).toContain("yfinance");
    expect(prompt.length).toBeGreaterThan(0);
  });

  test("has a heading for every section the page shows", () => {
    const md = toLlmMarkdown(candidate());
    for (const s of SECTIONS) expect(md).toContain(`## ${s}`);
  });

  test("writes numbers with units and dates as YYYY-MM-DD", () => {
    const md = toLlmMarkdown(candidate());
    expect(md).toContain("32.75 THB");
    expect(md).toContain("2026-10-14");
    expect(md).toContain("+12.3%");
    expect(md).not.toContain("2569");
    expect(md).toContain("Rank 3");
  });

  test("lists every exclusion reason and the failed gate with threshold and actual value", () => {
    const md = toLlmMarkdown(rejected());
    expect(md).toContain("ไม่ผ่าน quality gate");
    expect(md).toContain("median margin of safety 7.7% ต่ำกว่าเกณฑ์ 10%");
    expect(md).toMatch(/\| ROE \| FAIL \| ROE TTM ≥ 10% \| ROE TTM 6\.0% \\\| ต่ำกว่าเกณฑ์ \|/);
  });

  test("keeps N/A methods with their reason, and warning flags", () => {
    const md = toLlmMarkdown(rejected());
    expect(md).toMatch(/\| Dividend yield band.*\| N\/A \| N\/A \| ไม่ได้จ่ายปันผลเงินสดใน 12 เดือนล่าสุด \|/);
    expect(md).toContain("ส่วนผู้ถือหุ้น +69% ใน 2023Q2");
  });

  test("explains the methods it contains, including the cash dividend yield band", () => {
    const md = toLlmMarkdown(candidate());
    const notes = md.slice(md.indexOf("## Method notes"));
    expect(notes).toContain("MoS");
    expect(notes).toMatch(/cash dividends.*12 months.*median/i);
    expect(notes).toMatch(/stock dividends/i);
    expect(notes).not.toContain("pbv_median");
  });

  test("a failed stock still copies its status, hints and events", () => {
    const md = toLlmMarkdown(failed());
    expect(md).toContain("No data found");
    expect(md).toContain("## Catalyst hints");
    expect(md).toContain("ข่าวลงทุนหรือ M&A");
    expect(md).toContain("## Events");
    expect(md).not.toContain("## Fair value");
  });
});
