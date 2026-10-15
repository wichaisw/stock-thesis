import type { Evaluation, StockDetail } from "@/lib/engine";
import { pct } from "@/lib/format";
import { gateRows } from "@/lib/gates";

// English twin of FAIR_VALUE_HELP / MOS_HELP in app/stocks/[symbol]/page.tsx: change both together
export const METHOD_NOTES_EN: Record<string, string> = {
  pe_median:
    "PE band (median): the stock's own 5-year median PE × EPS TTM. PE history is market cap ÷ 4-quarter net profit. Suits steady earners, not cyclicals or fresh turnarounds.",
  pe_minus_1sd:
    "PE band (median − 1SD): (median PE − 1 standard deviation) × EPS TTM. A pessimistic view; price below it means a margin of safety even if the market dislikes the stock.",
  pbv_median:
    "PBV band (median): 5-year median PBV × latest book value per share. Suits asset-driven businesses (banks, finance, property), not asset-light ones or stocks whose ROE changed a lot.",
  dividend_yield_median:
    "Dividend yield band (median): cash dividends per share over the last 12 months ÷ median of the quarterly trailing 12-month cash yield over 5 years. Stock dividends are not counted, and quarters below the minimum yield are treated as not paying. A one-off special dividend can make it look cheap for about 12 months.",
  peer_pe:
    "Peer PE: median PE of other stocks in the same sector × EPS TTM. Cheap versus peers may reflect lower quality or growth, or the whole sector being expensive.",
  justified_pbv:
    "Justified PBV: (ROE TTM − g) ÷ (r − g) × latest equity per share, where r is the cost of equity and g the long-term growth (defaults 10% and 3%, set by the investor). Independent of past prices and usable for financials, but very sensitive to r − g, and a one-off profit inflates ROE and the fair value.",
};

const MOS_NOTE_EN =
  "MoS (margin of safety) = (fair value − price) ÷ fair value. Positive means the price is below that method's fair value. When a fair value is very low, the negative MoS looks exaggerated.";

const PROMPT = `You are giving a second opinion on a stock listed on the Stock Exchange of Thailand (SET).
The investor is a value investor who plans to hold for about one quarter, enters on CDC ActionZone timing, and filters candidates with pass/fail gates (never a weighted score). Fair value is a panel of methods, never one number.
The data below comes from the investor's own screening tool, built on unofficial sources (yfinance, thaifin), so it may contain errors.
Please:
1. Check the numbers for internal consistency and flag anything that looks wrong or suspicious.
2. Say which fair value methods suit this business and which do not.
3. Challenge the conclusion: give the strongest case against buying now, and what would change your mind.
Reply in Thai. Keep market terms (PE, PBV, MoS, ROE, CDC) in English.`;

const CHECK_LABELS: Record<string, string> = {
  min_quarters: "Statement quarters",
  roe: "ROE",
  de: "D/E",
  ocf: "OCF",
  no_loss: "No loss",
};

// locale-free so an LLM can't misread Buddhist-era years or Thai digit grouping
function thb(x: number | null | undefined): string {
  return x == null ? "N/A" : `${x.toFixed(2)} THB`;
}

function num(x: number | null | undefined, suffix = ""): string {
  return x == null ? "N/A" : `${x}${suffix}`;
}

function cell(s: string | null | undefined): string {
  return (s ?? "").replaceAll("|", "\\|").replaceAll("\n", " ");
}

function verdict(passed: boolean | null): string {
  return passed === null ? "SKIPPED" : passed ? "PASS" : "FAIL";
}

function gates(ev: Evaluation): string[] {
  const rows = gateRows(ev, `≥ ${ev.liquidity.threshold / 1e6} million THB/day`);
  const out = [
    `Quality gate: ${ev.quality ? verdict(ev.quality.passed) : "not evaluated (statements are fetched only after the liquidity gate passes)"}`,
    "",
    "| Gate | Result | Threshold | Actual |",
    "|---|---|---|---|",
    ...rows.map(
      (c) => `| ${c.name === "liquidity" ? "Liquidity" : (CHECK_LABELS[c.name] ?? c.name)} | ${verdict(c.passed)} | ${cell(c.threshold)} | ${cell(c.reason)} |`,
    ),
  ];
  if (ev.quality?.inflection.flag) out.push("", `Inflection: ${ev.quality.inflection.reason}`);
  return out;
}

function fairValue(fv: NonNullable<Evaluation["fair_value"]>): string[] {
  const s = fv.summary;
  const out = [
    `- Summary: ${s.label}`,
    `- MoS min / median / max: ${pct(s.min_mos)} / ${pct(s.median_mos)} / ${pct(s.max_mos)}`,
    `- Median fair value: ${thb(s.median_fair_value)}; max fair value: ${thb(s.max_fair_value)}`,
    `- EPS TTM: ${num(fv.eps_ttm, " THB")}`,
  ];
  if (fv.structure_change.flag) out.push(`- Warning, capital structure changed: ${fv.structure_change.reason}`);
  if (fv.history_gap?.flag) out.push(`- Warning, incomplete history: ${fv.history_gap.reason}`);
  out.push(
    "",
    "| Method | Fair value | MoS | Note |",
    "|---|---|---|---|",
    ...fv.items.map((i) => `| ${cell(i.label)} | ${thb(i.fair_value)} | ${pct(i.mos)} | ${cell(i.reason)} |`),
  );
  return out;
}

function cdc(c: Evaluation["cdc"]): string[] {
  if (c.state == null) return [`- Not available: ${c.reason}`];
  const out = [
    `- State: ${c.state}`,
    `- Fast EMA: ${c.fast?.toFixed(2) ?? "N/A"}`,
    `- Slow EMA: ${c.slow?.toFixed(2) ?? "N/A"}`,
    `- Gap (Slow − Fast) / Slow: ${pct(c.gap_pct, 2)}`,
    `- Gap narrowing speed: ${pct(c.speed, 2)} per day`,
    `- ETA to cross: ${num(c.eta_days, " trading days")}`,
  ];
  if (c.days_since_cross != null) out.push(`- Last cross: ${c.days_since_cross} trading days ago`);
  return out;
}

function riskReward(r: Evaluation["risk_reward"]): string[] {
  if (!r) return ["- Not available: no statement data"];
  const out = [
    `- Entry (last close): ${thb(r.entry)}`,
    `- Stop: ${thb(r.stop)}`,
    `- Target (median fair value): ${thb(r.target)}`,
    `- Target optimistic (max fair value): ${thb(r.target_optimistic)}`,
    `- RRR: ${num(r.rrr)}${r.low_rrr ? " (below the minimum RRR)" : ""}`,
    `- Upside: ${pct(r.upside)}${r.high_upside ? " (unusually high upside)" : ""}`,
  ];
  if (r.reason) out.push(`- Note: ${r.reason}`);
  return out;
}

export function toLlmMarkdown(d: StockDetail): string {
  const { stock, evaluation: ev, failure, hints, events } = d;
  const out = [
    PROMPT,
    "",
    "---",
    "",
    `# ${stock.symbol} — ${stock.name}`,
    "",
    `- Sector: ${stock.sector}`,
    `- Market: ${stock.market}`,
  ];
  if (ev)
    out.push(
      `- Last close: ${thb(ev.price)} on ${ev.price_date}${ev.stale_price ? " (stale: older than the latest price of other stocks in the same batch run)" : ""}`,
    );
  if (failure) out.push(`- Data fetch failed in the latest batch: ${failure}`);
  if (!ev && !failure) out.push("- No evaluation yet");

  if (ev) {
    out.push("", "## Candidate status", "");
    if (ev.candidate_rank != null) out.push(`- In the candidate list: Rank ${ev.candidate_rank}`);
    else out.push("- Not in the candidate list because:", ...ev.inclusion.reasons.map((r) => `  - ${r}`));
    out.push("", "## Gates", "", ...gates(ev));
    if (ev.fair_value) out.push("", "## Fair value", "", ...fairValue(ev.fair_value));
    out.push("", "## CDC ActionZone (daily)", "", ...cdc(ev.cdc));
    out.push("", "## Risk / reward", "", ...riskReward(ev.risk_reward));
  }

  out.push("", "## Catalyst hints", "");
  if (!hints.sector_matched) out.push("(No hints for this sector; showing general hints)");
  out.push(...hints.items.map((h) => `- ${h}`));

  out.push("", "## Events (next 6 months)", "");
  if (events.length === 0) out.push("- None");
  out.push(...events.map((e) => `- ${e.date}: ${e.label}${e.estimated ? " (estimated)" : ""}`));

  if (ev?.fair_value) {
    const notes = ev.fair_value.items.flatMap((i) => (METHOD_NOTES_EN[i.method] ? [`- ${METHOD_NOTES_EN[i.method]}`] : []));
    out.push("", "## Method notes", "", ...notes, `- ${MOS_NOTE_EN}`);
  }
  return out.join("\n") + "\n";
}
