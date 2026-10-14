---
name: data-crosscheck
description: Cross-check the engine's data sources (thaifin, yfinance, or a replacement such as SETSMART) against SET and TradingView for a fixed symbol set, then record the result in engine/README.md. Use before trusting a new source field (e.g. mkt_cap), after switching or upgrading a data source, or when a fair value or CDC value looks wrong.
---

# Data cross-check

Run the same comparison every time so results from different sessions and sources are comparable.

## Fixed symbol set

| Symbol | Why it is in the set |
|---|---|
| PTT | Stable share count (28.563B), big cap, regular dividends |
| CPALL | Stable share count, consumer |
| KBANK | Bank (financial-sector gate), stable share count |
| SCAP | Par split in 2022–2023, so per-share history is broken |
| GULF | Merger in 2Q25: equity +173%, share count changed |

Add a symbol only for the case being investigated (e.g. a candidate that looks wrong). Don't replace the set.

## Tolerance

- Price and market cap: within **2%** of the reference.
- EPS, BVPS, PE: within **2%**, or a match after rounding to SET's 2 decimals.
- CDC Fast/Slow: within rounding of TradingView (4 decimals).

A difference that **grows with age** (old quarters off more than recent ones) is a systematic adjustment, not noise. Report it as a mismatch even when recent quarters pass.

## Steps

1. **Source vs actual price.** Run the script from the repo root:

   ```bash
   uv run --project engine python .agents/skills/data-crosscheck/crosscheck.py \
     --shares PTT=28.563e9 --shares KBANK=2.369e9
   ```

   It prints, per quarter, thaifin `close`/`mkt_cap` beside the actual unadjusted quarter-end close from yfinance (`auto_adjust=False`). The `implied_shares` column is mkt_cap ÷ close. When `--shares` is given, the gap to the real market cap (actual close × shares) is shown too. Only pass `--shares` for symbols whose share count didn't change in the window.
2. **Reference share count and current market cap from SET.** Fetch `https://www.set.or.th/en/market/product/stock/quote/<SYMBOL>/factsheet`. It gives the current market cap and close, so shares = market cap ÷ close. Historical year-end figures are usually *not* on the page. Use step 1's real market cap for history.
3. **Statements.** For EPS (6M/9M/FY), BVPS and PE at the same price, compare with Company Highlights at `https://www.set.or.th/en/market/product/stock/quote/<SYMBOL>/financial-statement/company-highlights`.
4. **CDC (only when CDC code or the price source changed).** Compare Fast/Slow with TradingView's CDC ActionZone V3 2020 (`close 12 26 1`). Use the `orca-browser-check` skill to read the chart.
5. **Record.** Add a dated section under `## ผลตรวจข้อมูล` in `engine/README.md`, following the existing tables: one row per symbol in the form `engine / reference`, then a short "what didn't match" list.

## Stop rule

If anything is outside tolerance, **stop and report before changing code**. Report the table, the pattern (constant offset, grows with age, missing quarters, stale repeated values), and options. The user decides whether to change the source, the formula or the spec.
