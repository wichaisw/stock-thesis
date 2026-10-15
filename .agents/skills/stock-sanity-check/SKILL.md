---
name: stock-sanity-check
description: After a batch run, scan every evaluation and quarterly row in engine/shortlist.db for outliers that mean a bug or bad source data (MoS below −100%, fair value far above price, missing or stale repeated values). Use after running the batch, after changing core/fair_value or a source adapter, and before trusting the candidate list in the UI.
---

# Stock sanity check

Catches bugs like SKY's dividend yield band, which gave a fair value of 1,533 baht at a price of 17.40, before they show up in the UI.

## Steps

1. Run the batch, or skip this step if a fresh successful run already exists:

   ```bash
   cd engine && uv run shortlist-batch
   ```

2. Scan the latest successful run:

   ```bash
   uv run --project engine python .agents/skills/stock-sanity-check/sanity.py
   ```

   It exits 1 when any flag is found. `--candidates-only` limits the scan to the candidate list.

3. For each flagged symbol, open the detail page or the raw rows and decide which case it is:
   - **Formula bug** (e.g. a band built from too few points): fix it with a test that reproduces the row.
   - **Source data** (missing, stale or adjusted values): cross-check it with the `data-crosscheck` skill.
   - **Real business change** (merger, near-zero earnings): this is expected. Make sure the UI warns about it.

4. Report the flag counts per rule and what each flagged symbol turned out to be. Don't silence a rule to get a clean run. Change a threshold only with the user's agreement.

5. After changing `core/fair_value`, also run the `fair-value-backtest` skill and compare with the previous file in `docs/backtests/`.

## Rules

| Rule | Why |
|---|---|
| MoS < −100% on any method | Fair value is less than half the price, so the band is likely degenerate (e.g. CCET −341%) |
| fair value > 5× price | Median near zero in a denominator (e.g. SKY's yield band) |
| Missing value in the last 4 quarters of a used field | Gaps in thaifin, e.g. mkt_cap missing for 2025Q1–Q2 |
| Same non-zero value in consecutive quarters | Stale copy, e.g. GULF's mkt_cap in 2025Q1 repeats 2024Q4 |
| Equity change > 50% between quarters | Should carry the structure-change warning; flagged if it doesn't |
