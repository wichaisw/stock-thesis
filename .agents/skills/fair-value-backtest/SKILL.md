---
name: fair-value-backtest
description: Measure how well the fair value panel and the candidate rule predicted the next quarter, at every quarter end from 2021Q1 to 2026Q2, using the engine's own code on data known at each date (no look-ahead). Writes docs/backtests/fair-value-<date>.md. Use after changing core/fair_value, core/quality, a fair value threshold or a statement source, and to compare against the previous result file.
---

# Fair value backtest

Runs `fair_value.evaluate` and `quality.evaluate` as of each quarter end, using only statements past their filing deadline (45 days, or 60 for Q4) and prices and market caps up to that date. It then scores the result over the next 63 trading days (one quarter, per the thesis). The logic is in `engine/shortlist/backtest.py`. This script only fetches data, caches it and writes the file.

## Steps

1. Run it. The first run fetches 8 years of prices for the whole market, plus statements and market caps for about 400 stocks (several minutes). Later runs use `engine/.cache/fv-backtest/`. Pass `--refresh` to fetch everything again.

   ```bash
   uv run --project engine python .agents/skills/fair-value-backtest/backtest.py
   ```

2. If it exits with `look-ahead: ...`, **stop**. Some evaluation changed when the data after the test date changed. Fix the data cut in `shortlist/backtest.py` first, with a test that reproduces the leak. The script writes no result file in this case. Don't read anything into earlier results until the fix is in.

3. Check the excluded share in `## หุ้นที่ตัด`. If it is above about 30% of the stocks, tell the user before drawing conclusions: the result then covers only the stocks that are left.

4. Compare with the previous file in `docs/backtests/` (same commit? same cache date?) and report the main numbers per method.

## Reading the result

| Metric | Meaning | Look for |
|---|---|---|
| hit (n) | Of evaluations with MoS > 0, % where the High within 63 days reached the fair value | Higher MoS buckets should not hit far less often (a fair value set too high) |
| excess | Mean 63-day total return of the group with MoS ≥ `min_gate_mos`, minus the equal-weight mean of every stock evaluated that day. Taken per date, then summarized across dates | Mean and median both > 0, with most dates positive |
| สลับ MoS (placebo) | The same excess after shuffling MoS among the stocks of each date, averaged over 20 shuffles | Near 0. If not, the measurement itself is biased: don't trust the real rows |
| bucket | Count, hit rate, median return and median excess per MoS bucket (< 0, 0–10%, 10–30%, ≥ 30%) | Returns rising with MoS means the method ranks stocks |
| gate | Lowest MoS of the computable gate methods (`candidates.gate_methods`), scored like a method | The value the candidate rule, the sort and the target read |
| candidate | The live rule: passed quality and every computable gate method has MoS ≥ `min_gate_mos`, at least one computable (CDC is not part of it). Hit is measured against the gate's fair value | Excess > 0 is the evidence behind "the profit comes from fundamentals and MoS" |
| candidate (median) | The old rule, kept for comparison: passed quality and median MoS ≥ `min_gate_mos` | If it beats `candidate` (or `candidate`'s CI crosses 0), tell the user: the gate rule needs a review (its two methods were picked in-sample) |
| 95% CI, t | Range of the mean excess from resampling the test dates 2,000 times, and mean ÷ standard error across dates | CI above 0 (or t above ~2). With about 48 CIs in one file, about 2 clear 0 by chance: one alone is a hypothesis, not proof |
| candidate (relative) | Passed quality and median MoS in the top 20% of that date's evaluated stocks, no MoS floor. Backtest only | Beats `candidate` on the 63-day row and in the clean table, with a placebo near 0. The per-date `candidate %` column shows how far the absolute gate drifts |
| candidate MoS ≥ 15/20/25%, Option A, Option B, quality ผ่านทุกข้อ (+ D/E ≤ 2.0) | Backtest-only variants of `candidate` (`VARIANTS` in `backtest.py`), each changing one thing. Option A: one gate method ≥ 15% and the other ≥ −10%, a single computable one ≥ 12%. Option B: both computable, mean ≥ 8%, none < −15%. Hit is measured against the gate's fair value, as for `candidate` | Read them in the variant table, not here. Option A/B hit rates look high because the gate's fair value can be below the price |
| ผลรวมแบบไม่นับค่าผิดปกติ | The summary again with abnormal evaluations dropped from each group, same baseline | A group that wins only in the main table is winning on bad data |
| ต่อระยะวัดผล | Excess, CI and t at 63, 126 and 252 trading days; the bucket table adds median excess at 126 and 252 | 63 days decides (the thesis). Longer windows overlap, so their t looks better than it is. High-MoS buckets turning positive only at 252 means slow, not wrong |
| คำนวณไม่ได้ | The method gave no fair value | Early dates have fewer band points, since share counts start in Nov 2018 |
| ค่าประเมินผิดปกติ | MoS < −100% or fair value > 5× price. Still counted in every metric | The same bugs `stock-sanity-check` hunts for |

## Reading the variant table (`## variant ของ candidate rule`)

The first table splits `candidate` and every variant into 2021Q1–2023Q4 and 2024Q1 onwards. The second gives each variant's paired difference (per-date excess of the variant − `candidate`, on dates both have picks) and the verdict.

A variant passes only when all of these hold (fixed before the first run, design D4 of `validate-gate-variants`): its mean 63-day excess beats `candidate` in both halves, the lower end of its full-period 95% CI is above 0, and it averages at least 3 candidates per date with picks on at least 80% of dates. The paired difference is shown alongside but is not part of the rule.

- The split is a stability check, **not out-of-sample**. The gate methods and the 10% threshold were chosen on both halves. Only `candidate_history` (from 15 Oct 2026) is truly unseen data.
- A variant that wins only one half usually tracks the market regime, not a better rule.
- A pass is a reason to propose a change, not to edit `engine/config.yaml`. The user decides in a separate OpenSpec change.

## Reading the profit-jump table (`## ป้ายกำไรกระโดด`)

`candidate` split into stocks with and without the profit-jump tag (`flags.profit_jump_ratio`, computed by the same `quality.profit_jump` as the batch), per half. The tag "carries information" (`ป้ายมีข้อมูล: ใช่`) only when tagged candidates have a lower mean excess than untagged ones in both halves, a rule fixed before the first run (design D5 of `add-risk-flags`).

- It is a tag, not a gate: a "ใช่" is a reason to propose a gate change, never to make one.
- Check `หุ้นเฉลี่ย/วันที่` of the tagged rows. Few tagged stocks per date make that row's CI too wide to read.
- The backtest tags on thaifin profit only; the batch overlays yfinance on the latest quarters, so live tags can differ.

## Reading the bank table (`## candidate นอกธนาคาร`)

`candidate` split into sector `Banking` and everything else, per half and for the whole period. Other financials (Finance & Securities, Insurance) count outside Banking. The baseline still includes the banks. "edge นอกธนาคาร: มี" means the non-bank rows have a positive mean excess in both halves and a whole-period 95% CI lower bound above 0. They do not need to beat `candidate` (design D1–D4 of `backtest-ex-banking-variant`).

- The rule was set after one exploratory look at the same data (2026-10-27), so it is a pre-set rule only for later runs. It is not out-of-sample.
- The first run passed by a hair (lower bound +0.003%). Compare the non-bank whole-period row between runs, not just the verdict.
- "ไม่มี" means the candidate rule has no evidence outside the banks. Report it and ask the user. It is never a reason to change the gate here.
- The sector is the stock's latest one from thaifin, not the one it had on the test date.

There are only 22 test dates, and evaluations of one stock on consecutive dates are not independent. A difference of a few percentage points between runs is noise.

## Stop rules

- A failed poison check means fix the bug first. Never skip it or loosen it.
- A result is never a reason to change a formula or threshold on your own. Report it and ask the user. A change prompted by a backtest is its own OpenSpec change.
- Never add, drop or retune a variant, or change the adoption rule, after seeing a result. That is choosing on the test data. It needs its own change, and the next run is the test.
- Results are committed (`docs/backtests/`). The cache is not (`engine/.cache/`).
