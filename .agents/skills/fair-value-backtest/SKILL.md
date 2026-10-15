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
| ผลรวมแบบไม่นับค่าผิดปกติ | The summary again with abnormal evaluations dropped from each group, same baseline | A group that wins only in the main table is winning on bad data |
| ต่อระยะวัดผล | Excess, CI and t at 63, 126 and 252 trading days; the bucket table adds median excess at 126 and 252 | 63 days decides (the thesis). Longer windows overlap, so their t looks better than it is. High-MoS buckets turning positive only at 252 means slow, not wrong |
| คำนวณไม่ได้ | The method gave no fair value | Early dates have fewer band points, since share counts start in Nov 2018 |
| ค่าประเมินผิดปกติ | MoS < −100% or fair value > 5× price. Still counted in every metric | The same bugs `stock-sanity-check` hunts for |

There are only 22 test dates, and evaluations of one stock on consecutive dates are not independent. A difference of a few percentage points between runs is noise.

## Stop rules

- A failed poison check means fix the bug first. Never skip it or loosen it.
- A result is never a reason to change a formula or threshold on your own. Report it and ask the user. A change prompted by a backtest is its own OpenSpec change.
- Results are committed (`docs/backtests/`). The cache is not (`engine/.cache/`).
