"""Fair value backtest (openspec backtest-fair-value): pure logic only, the skill's script fetches and caches the data.

Each test date T is a quarter end. The engine's own `fair_value`/`quality` code runs on data cut to what was
known at T (design D2), and the outcome is read from the 63 trading days after T.
"""

import math
import random
import statistics
from collections.abc import Callable
from dataclasses import dataclass, replace

import pandas as pd

from shortlist.config import Catalyst, Config
from shortlist.core import fair_value, quality
from shortlist.sources import StockInfo

HORIZON = 63
# 63 stays the thesis horizon; the longer ones only show whether a high MoS was wrong or just slow (design D2)
HORIZONS = (HORIZON, 126, 252)
MEDIAN = "median"  # the panel's median MoS, scored like a method
GATE = "gate"  # lowest MoS of the computable gate methods, scored like a method (gate-on-proven-methods D5)
CANDIDATE = "candidate"  # quality passed and every computable gate method's MoS ≥ candidates.min_gate_mos
CANDIDATE_MEDIAN = "candidate (median)"  # the old rule kept for comparison: quality passed and median MoS ≥ min_gate_mos
RELATIVE = "candidate (relative)"  # quality passed and median MoS in the date's top RELATIVE_TOP (design D4)
RELATIVE_TOP = 0.20
BOOTSTRAP = 2000
# same rules as the stock-sanity-check skill
ABNORMAL_MOS = -1.0
ABNORMAL_FV_TO_PRICE = 5.0
# fixed edges so runs compare (design D9); 10% is candidates.min_gate_mos
BUCKETS = [(-math.inf, 0.0, "< 0"), (0.0, 0.10, "0–10%"), (0.10, 0.30, "10–30%"), (0.30, math.inf, "≥ 30%")]
POISON_FACTOR = 1000
# one shuffle of ~14 stocks per date swings ±4% by chance; the mean of 20 settles near the true offset
PLACEBO_SEEDS = 20
LIMITATIONS = [
    "survivorship bias: หุ้นที่ถูกถอนไม่มีใน yfinance ทั้งกลุ่มและ baseline จึงดูดีเกินจริง excess return ลำเอียงน้อยกว่าผลตอบแทนดิบ แต่ยังลำเอียง",
    "งบ thaifin เป็นค่าล่าสุด ถ้าถูก restate ย้อนหลัง ค่าที่ T เป็นค่าใหม่ ไม่ใช่ค่าที่ประกาศจริง ณ ตอนนั้น (poison check จับไม่ได้)",
    "ใช้งบ thaifin อย่างเดียว ไม่ใช้งบ yfinance ที่ batch ใช้ปัจจุบัน ผลจึงอาจต่างจาก batch จริงในไตรมาสล่าสุด",
    "การประเมินของหุ้นตัวเดียวกันในวันที่ติดกันไม่เป็นอิสระต่อกัน จำนวนการประเมินจึงดูมากกว่าข้อมูลที่เป็นอิสระจริง",
    "จำนวนหุ้นจาก yfinance เริ่ม พ.ย. 2018 วันที่ทดสอบช่วงต้นมีจุดใน band น้อยกว่า 20 (ดูจำนวนที่คำนวณได้ต่อวันที่)",
    "ตัดหุ้นที่ split, ปันผลเป็นหุ้น หรือ merge ออกทั้งตัว ผลจึงเป็นของหุ้นที่เหลือเท่านั้น",
    "ไม่จำลองการเทรด ไม่มีค่าธรรมเนียม slippage stop หรือ CDC",
    "ที่ 126 และ 252 วัน ช่วงวัดผลของวันที่ทดสอบที่ติดกันซ้อนกัน excess ต่อวันที่จึงไม่เป็นอิสระ t และช่วงความเชื่อมั่นดูแน่นอนกว่าจริง",
    "เทียบหลายกลุ่มหลายระยะ (ราว 48 ช่วงความเชื่อมั่น) ราว 2 ช่วงจะไม่คร่อม 0 ได้โดยบังเอิญ ตัวตัดสินหลักคือตารางผลรวม 63 วัน",
]


@dataclass(frozen=True)
class StockData:
    info: StockInfo
    prices: pd.DataFrame  # PRICE_COLUMNS + adj_close, by date
    splits: pd.Series  # yfinance "Stock Splits" (stock dividends count as splits), by date
    quarterly: pd.DataFrame
    caps: pd.DataFrame


class LookAhead(Exception):
    """Poison check found an evaluation that changed when data after T changed."""


Cut = Callable[[StockData, pd.Timestamp, Catalyst], StockData]


def quarter_ends(start: str, end: str) -> list[pd.Timestamp]:
    return [p.end_time.normalize() for p in pd.period_range(start, end, freq="Q")]


def excluded(stocks: dict[str, StockData], start: str, end: str, threshold: float) -> dict[str, str]:
    """Stocks whose prices or bands are not comparable across the test range (design D3), with why."""
    first = str(pd.Period(start, "Q") - 1)  # so a change into the first quarter counts
    out = {}
    for sym, s in stocks.items():
        splits = s.splits[s.splits.fillna(0) != 0]
        if len(splits):
            out[sym] = f"split หรือปันผลเป็นหุ้น {splits.index[0]:%Y-%m-%d} ratio {splits.iloc[0]:g}"
            continue
        reported = s.quarterly[s.quarterly["eps"].notna()]
        equity = reported.loc[(reported.index >= first) & (reported.index <= end), "equity"]
        change = equity.pct_change().abs()
        if change.max() > threshold:
            out[sym] = f"ส่วนผู้ถือหุ้นเปลี่ยน {change.max():.0%} ใน {change.idxmax()}"
    return out


def available_on(quarter: str, cfg: Catalyst) -> pd.Timestamp:
    """Filing deadline of a quarter's statement: the earliest day the backtest may use it."""
    p = pd.Period(quarter, "Q")
    days = cfg.annual_deadline_days if p.quarter == 4 else cfg.quarter_deadline_days
    return p.end_time.normalize() + pd.Timedelta(days=days)


def cut(s: StockData, t: pd.Timestamp, cfg: Catalyst) -> StockData:
    """Only what was known at T. Splits stay whole: exclusion reads the full history by design."""
    due = [available_on(q, cfg) <= t for q in s.quarterly.index]
    return replace(
        s,
        prices=s.prices[s.prices.index <= t],
        quarterly=s.quarterly.loc[due],  # .loc: an empty list in [] selects zero columns, not zero rows
        caps=s.caps[s.caps.index <= str(t.to_period("Q"))],
    )


def cap_gap(quarterly: pd.DataFrame, caps: pd.DataFrame, lookback: int) -> str | None:
    """Quarters without a market cap between the first and last ones that have it. Quarters before the share
    count starts (Nov 2018) only mean fewer band points, so they are not a gap (user decision, design D3).
    Trailing ones aren't either: skipping on them would hide a leaked statement from the poison check."""
    hist = quarterly[quarterly["eps"].notna()].join(caps[["mkt_cap"]]).tail(lookback)
    has = hist["mkt_cap"].notna()
    missing = hist.index[has.cummax() & has[::-1].cummax()[::-1] & ~has]
    return f"market cap ขาดใน {', '.join(missing)}" if len(missing) else None


def abnormal(fv: float | None, mos: float | None, price: float) -> bool:
    return fv is not None and ((mos is not None and mos < ABNORMAL_MOS) or fv > ABNORMAL_FV_TO_PRICE * price)


def evaluate_date(
    stocks: dict[str, StockData], t: pd.Timestamp, cfg: Config, cut: Cut = cut
) -> tuple[list[dict], dict[str, str]]:
    """One row per stock per method (plus MEDIAN and GATE) for stocks liquid at T, and the stocks skipped for a cap gap."""
    at = {sym: cut(s, t, cfg.catalyst) for sym, s in stocks.items()}
    liquid = {
        sym: s for sym, s in at.items()
        if len(s.prices) and quality.liquidity(s.prices, cfg.liquidity)["passed"]
    }
    price = {sym: float(s.prices["close"].iloc[-1]) for sym, s in liquid.items()}
    pe_by_symbol = {
        sym: (s.info.sector, fair_value.current_pe(s.quarterly, price[sym], s.caps)) for sym, s in liquid.items()
    }
    rows, skipped = [], {}
    for sym, s in liquid.items():
        if gap := cap_gap(s.quarterly, s.caps, cfg.fair_value.lookback_quarters):
            skipped[sym] = gap
            continue
        peers = fair_value.peers_for(sym, s.info.sector, pe_by_symbol)
        fv = fair_value.evaluate(s.quarterly, price[sym], peers, cfg.fair_value, s.caps)
        passed = quality.evaluate(s.quarterly, s.info.sector, cfg.quality)["passed"]
        summary = fv["summary"]
        gate = fair_value.gate(fv["items"], cfg.candidates.gate_methods)
        min_mos = cfg.candidates.min_gate_mos
        candidate = passed and gate["mos"] is not None and gate["mos"] >= min_mos
        candidate_median = passed and summary["median_mos"] is not None and summary["median_mos"] >= min_mos
        items = [(i["method"], i["fair_value"], i["mos"]) for i in fv["items"]]
        items.append((MEDIAN, summary["median_fair_value"], summary["median_mos"]))
        items.append((GATE, gate["fair_value"], gate["mos"]))
        for method, value, mos in items:
            rows.append({
                "date": t, "symbol": sym, "method": method, "price": price[sym], "fair_value": value, "mos": mos,
                "quality_passed": passed, "candidate": candidate, "candidate_median": candidate_median,
                "abnormal": abnormal(value, mos, price[sym]),
            })
    top = top_share({r["symbol"]: r["mos"] for r in rows if r["method"] == MEDIAN})
    for r in rows:
        r["relative"] = r["quality_passed"] and r["symbol"] in top
    return rows, skipped


def top_share(mos: dict[str, float | None]) -> set[str]:
    """Symbols whose MoS ranks in the top RELATIVE_TOP of those that have one (design D4)."""
    ranks = pd.Series({k: v for k, v in mos.items() if v is not None}, dtype=float).rank(pct=True)
    return set(ranks[ranks > 1 - RELATIVE_TOP].index)


def outcome(prices: pd.DataFrame, t: pd.Timestamp, horizon: int = HORIZON) -> tuple[float, float] | None:
    """Total return (Adj Close) to the horizon-th trading day after T, and the highest High of days 1..horizon.
    None until the horizon has passed."""
    i = int(prices.index.searchsorted(t, side="right"))
    if i == 0 or i + horizon > len(prices):
        return None
    adj = prices["adj_close"]
    return float(adj.iloc[i + horizon - 1] / adj.iloc[i - 1] - 1), float(prices["high"].iloc[i : i + horizon].max())


def ret_col(horizon: int) -> str:
    return "ret" if horizon == HORIZON else f"ret_{horizon}"


def with_outcomes(rows: pd.DataFrame, prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """`ret` and `max_high` at HORIZON, and `ret_<h>` at each longer horizon."""
    keys = list(zip(rows["symbol"], rows["date"]))
    out = rows.copy()
    for h in HORIZONS:
        got = {k: outcome(prices[k[0]], k[1], h) for k in set(keys)}
        out[ret_col(h)] = [(got[k] or (None, None))[0] for k in keys]
        if h == HORIZON:
            out["max_high"] = [(got[k] or (None, None))[1] for k in keys]
    return out


CANDIDATE_GROUPS = [(CANDIDATE, GATE, "candidate"), (CANDIDATE_MEDIAN, MEDIAN, "candidate_median"), (RELATIVE, MEDIAN, "relative")]
CANDIDATE_NAMES = {name for name, _, _ in CANDIDATE_GROUPS}


def bucket(mos: float) -> str:
    return next(label for lo, hi, label in BUCKETS if lo <= mos < hi)


def groups(rows: pd.DataFrame, min_mos: float) -> dict[str, pd.DataFrame]:
    """Per method (plus MEDIAN, GATE and the candidate groups): its computed rows with `selected` = in the group
    whose excess is scored. Each candidate group reads the row of its own rule, so hit and abnormal follow that rule."""
    out = {}
    for method in rows["method"].unique():
        g = rows[(rows["method"] == method) & rows["mos"].notna()].copy()
        g["selected"] = g["mos"] >= min_mos
        out[method] = g
    for name, method, flag in CANDIDATE_GROUPS:
        g = rows[rows["method"] == method].copy()
        g["selected"] = g[flag]
        out[name] = g
    return out


def shuffled(g: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Placebo (design D10): the selection reshuffled among the stocks of each date."""
    rng = random.Random(seed)
    out = g.copy()
    for _, idx in out.groupby("date").groups.items():
        flags = out.loc[idx, "selected"].tolist()
        rng.shuffle(flags)
        out.loc[idx, "selected"] = flags
    return out


def excess(g: pd.DataFrame, baseline: pd.Series, ret: str = "ret", spread: bool = False) -> dict:
    """Per date: mean return of the selected stocks − that date's equal-weight baseline, then summarized
    across dates so every quarter weighs the same (design D5). `spread` adds t and the 95% CI."""
    per_date = g[g["selected"]].groupby("date")[ret].mean() - baseline
    per_date = per_date.dropna()
    out = {"dates": len(per_date), "mean": None, "median": None, "positive": None}
    if len(per_date):
        out |= {
            "mean": float(per_date.mean()),
            "median": float(per_date.median()),
            "positive": float((per_date > 0).mean()),
        }
    return out | uncertainty(per_date.tolist()) if spread else out


def uncertainty(x: list[float], seed: int = 0) -> dict:
    """t of the mean and its 95% CI by resampling dates (design D1: no scipy for one quantile)."""
    if len(x) < 2:
        return {"t": None, "ci_low": None, "ci_high": None}
    se = statistics.stdev(x) / math.sqrt(len(x))
    rng = random.Random(seed)
    cuts = statistics.quantiles([statistics.fmean(rng.choices(x, k=len(x))) for _ in range(BOOTSTRAP)], n=40)
    return {"t": statistics.fmean(x) / se if se else None, "ci_low": cuts[0], "ci_high": cuts[-1]}


def summarize(done: pd.DataFrame, baseline: pd.Series, min_mos: float, seed: int, uncomputed: pd.Series) -> pd.DataFrame:
    """One summary row per group at HORIZON: evaluations, hit rate, excess with t/CI and its placebo."""
    out = []
    for name, g in groups(done, min_mos).items():
        up = g[g["selected"]] if name in CANDIDATE_NAMES else g[g["mos"] > 0]
        hits = up["max_high"] >= up["fair_value"]
        real = excess(g, baseline, spread=True)
        runs = [excess(shuffled(g, seed + i), baseline) for i in range(PLACEBO_SEEDS)]
        placebo = {k: runs[0][k] if k == "dates" or runs[0][k] is None else sum(r[k] for r in runs) / len(runs)
                   for k in runs[0]}
        out.append({
            "group": name, "evaluations": len(g), "uncomputed": int(uncomputed.get(name, 0)),
            "hit_n": len(up), "hit_rate": float(hits.mean()) if len(up) else None,
            **{f"excess_{k}": v for k, v in real.items()},
            **{f"placebo_{k}": v for k, v in placebo.items()},
        })
    return pd.DataFrame(out)


def metrics(rows: pd.DataFrame, min_mos: float, seed: int = 0) -> dict[str, pd.DataFrame]:
    """`rows` from evaluate_date + with_outcomes. Evaluations whose horizon has not passed are not counted.
    `clean` drops abnormal evaluations from the groups but keeps every stock in the baseline (design D3)."""
    uncomputed = rows[rows["fair_value"].isna()].groupby("method").size()
    baselines = {}
    for h in HORIZONS:
        col = ret_col(h)
        baselines[h] = rows[(rows["method"] == MEDIAN) & rows[col].notna()].groupby("date")[col].mean()
    baseline = baselines[HORIZON]
    done = rows[rows["ret"].notna()]
    by_horizon = []
    for h in HORIZONS:
        col = ret_col(h)
        for name, g in groups(rows[rows[col].notna()], min_mos).items():
            by_horizon.append({"group": name, "horizon": h, **excess(g, baselines[h], col, spread=True)})
    buckets = []
    for name, g in groups(done, min_mos).items():
        if name in CANDIDATE_NAMES:
            continue
        g = g.assign(bucket=g["mos"].map(bucket), excess=g["ret"] - g["date"].map(baseline),
                     **{f"excess_{h}": g[ret_col(h)] - g["date"].map(baselines[h]) for h in HORIZONS[1:]})
        for _, _, label in BUCKETS:
            b = g[g["bucket"] == label]
            b_up = b[b["mos"] > 0]
            buckets.append({
                "group": name, "bucket": label, "n": len(b),
                "hit_rate": float((b_up["max_high"] >= b_up["fair_value"]).mean()) if len(b_up) else None,
                "median_ret": float(b["ret"].median()) if len(b) else None,
                "median_excess": float(b["excess"].median()) if len(b) else None,
                **{f"median_excess_{h}": float(b[f"excess_{h}"].median()) if b[f"excess_{h}"].notna().any() else None
                   for h in HORIZONS[1:]},
            })
    return {
        "summary": summarize(done, baseline, min_mos, seed, uncomputed),
        "clean": summarize(done[~done["abnormal"]], baseline, min_mos, seed, uncomputed),
        "horizons": pd.DataFrame(by_horizon),
        "buckets": pd.DataFrame(buckets),
        "baseline": baseline,
    }


def poison(s: StockData, t: pd.Timestamp, cfg: Catalyst) -> StockData:
    """Every row not known at T multiplied by POISON_FACTOR: an evaluation that changes read the future."""

    def spoil(df: pd.DataFrame, after) -> pd.DataFrame:
        df = df.copy()
        cols = df.select_dtypes("number").columns
        df.loc[after, cols] = df.loc[after, cols] * POISON_FACTOR
        return df

    return replace(
        s,
        prices=spoil(s.prices, s.prices.index > t),
        quarterly=spoil(s.quarterly, [available_on(q, cfg) > t for q in s.quarterly.index]),
        caps=spoil(s.caps, s.caps.index > str(t.to_period("Q"))),
    )


def _keyed(rows: list[dict], skipped: dict[str, str]) -> dict:
    out = {(r["symbol"], r["method"]): (r["fair_value"], r["mos"], r["quality_passed"], r["candidate"], r["candidate_median"])
           for r in rows}
    out.update({(sym, "skipped"): reason for sym, reason in skipped.items()})
    return out


def poison_check(
    stocks: dict[str, StockData], dates: list[pd.Timestamp], cfg: Config, n: int = 5, seed: int = 0, cut: Cut = cut
) -> list[pd.Timestamp]:
    """Raises LookAhead naming the stock, date and method when any evaluation differs. Returns the dates checked."""
    picked = sorted(random.Random(seed).sample(dates, min(n, len(dates))))
    for t in picked:
        clean = _keyed(*evaluate_date(stocks, t, cfg, cut))
        dirty = _keyed(*evaluate_date({k: poison(s, t, cfg.catalyst) for k, s in stocks.items()}, t, cfg, cut))
        diff = [k for k in clean.keys() | dirty.keys() if clean.get(k) != dirty.get(k)]
        if diff:
            sym, method = sorted(diff)[0]
            raise LookAhead(
                f"look-ahead: {sym} {t:%Y-%m-%d} {method}: {clean.get((sym, method))} → {dirty.get((sym, method))} "
                f"(ต่าง {len(diff)} ค่า)"
            )
    return picked


def _pct(x: float | None, digits: int = 1) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:+.{digits}%}"


def _rate(x: float | None) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.0%}"


def _ci(low: float | None, high: float | None) -> str:
    return "–" if low is None else f"{_pct(low)} ถึง {_pct(high)}"


def _t(x: float | None) -> str:
    return "–" if x is None else f"{x:.2f}"


SUMMARY_HEADER = ["กลุ่ม", "การประเมิน", "คำนวณไม่ได้", "hit (n)", "วันที่", "excess เฉลี่ย", "excess median",
                  "% วันที่บวก", "95% CI", "t"]


def _summary_rows(s: pd.DataFrame) -> list[list]:
    out = []
    for r in s.itertuples():
        out.append([r.group, r.evaluations, r.uncomputed, f"{_rate(r.hit_rate)} ({r.hit_n})", r.excess_dates,
                    _pct(r.excess_mean), _pct(r.excess_median), _rate(r.excess_positive),
                    _ci(r.excess_ci_low, r.excess_ci_high), _t(r.excess_t)])
        out.append([f"{r.group} (สลับ MoS)", "", "", "", r.placebo_dates, _pct(r.placebo_mean),
                    _pct(r.placebo_median), _rate(r.placebo_positive), "", ""])
    return out


def _table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def report(
    *,
    meta: dict,
    cfg: Config,
    dates: list[pd.Timestamp],
    universe: int,
    excluded: dict[str, str],
    failures: dict[str, str],
    skipped: dict[pd.Timestamp, dict[str, str]],
    poisoned: list[pd.Timestamp],
    rows: pd.DataFrame,
    result: dict[str, pd.DataFrame],
) -> str:
    """Markdown of one run. `meta`: run_date, commit, dirty (bool), cache_date. `universe`: stocks ever liquid
    in the range whose data was fetched, before exclusion."""
    commit = meta["commit"] + (" (มีการแก้ที่ยังไม่ commit)" if meta["dirty"] else "")
    fv, cand = cfg.fair_value, cfg.candidates
    evaluated = rows[rows["method"] == MEDIAN]
    by_reason = {"split/ปันผลเป็นหุ้น": 0, "ส่วนผู้ถือหุ้นเปลี่ยน": 0}
    for reason in excluded.values():
        by_reason["split/ปันผลเป็นหุ้น" if reason.startswith("split") else "ส่วนผู้ถือหุ้นเปลี่ยน"] += 1
    share = len(excluded) / universe if universe else 0.0

    longer = HORIZONS[1:]
    horizon_rows = [[r.group, r.horizon, r.dates, _pct(r.mean), _ci(r.ci_low, r.ci_high), _t(r.t)]
                    for r in result["horizons"].sort_values(["group", "horizon"], kind="stable").itertuples()]
    bucket_rows = [[r.group, r.bucket, r.n, _rate(r.hit_rate), _pct(r.median_ret), _pct(r.median_excess)]
                   + [_pct(getattr(r, f"median_excess_{h}")) for h in longer]
                   for r in result["buckets"].itertuples()]
    methods = [m for m in fv.enabled]
    computed = rows[rows["fair_value"].notna()].groupby(["date", "method"]).size()
    per_date = []
    for t in dates:
        day = evaluated[evaluated["date"] == t]
        n_cand, n_med, n_rel = (int(day[c].sum()) for c in ("candidate", "candidate_median", "relative"))
        total = len(day) or None
        per_date.append([f"{t:%Y-%m-%d}", len(day), len(skipped.get(t, {})), n_cand,
                         _pct(result["baseline"].get(t))] + [int(computed.get((t, m), 0)) for m in methods]
                        + [_rate(total and n_cand / total), n_med, _rate(total and n_med / total),
                           n_rel, _rate(total and n_rel / total)])
    odd = rows[rows["abnormal"]].sort_values(["date", "symbol", "method"])
    odd_rows = [[f"{r.date:%Y-%m-%d}", r.symbol, r.method, f"{r.price:,.2f}", f"{r.fair_value:,.2f}", _pct(r.mos, 0)]
                for r in odd.itertuples()]

    parts = [
        f"# Fair value backtest {meta['run_date']}",
        "## การตั้งค่า",
        "\n".join([
            f"- commit: `{commit}`",
            f"- วันที่ของ cache: {meta['cache_date']}",
            f"- วันที่ทดสอบ: {dates[0]:%Y-%m-%d} ถึง {dates[-1]:%Y-%m-%d} ({len(dates)} วัน สิ้นไตรมาส) วัดผลที่ {HORIZON} วันทำการ "
            f"(ตัวประกอบ {', '.join(str(h) for h in longer)} วัน)",
            f"- เกณฑ์: liquidity ≥ {cfg.liquidity.min_avg_traded_value / 1e6:,.0f} ลบ./วัน ({cfg.liquidity.window_days} วัน), "
            f"candidate = ผ่าน quality และทุก gate method ({', '.join(cand.gate_methods)}) ที่คำนวณได้มี MoS ≥ {cand.min_gate_mos:.0%} "
            f"(คำนวณได้อย่างน้อย 1 ตัว), candidate (median) = rule เดิม ผ่าน quality และ median MoS ≥ {cand.min_gate_mos:.0%}, "
            f"candidate (relative) = ผ่าน quality และ median MoS อยู่ใน {RELATIVE_TOP:.0%} บนของวันนั้น, method {', '.join(fv.enabled)}, "
            f"lookback {fv.lookback_quarters} ไตรมาส, min_history_points {fv.min_history_points}, "
            f"structure_change_threshold {fv.structure_change_threshold:.0%}, กำหนดส่งงบ {cfg.catalyst.quarter_deadline_days} วัน "
            f"(Q4 {cfg.catalyst.annual_deadline_days} วัน)",
            f"- หุ้นที่เคยผ่าน liquidity และดึงข้อมูลได้ {universe} ตัว ตัดออก {len(excluded)} ตัว ({share:.0%}) "
            f"ประเมิน {evaluated['symbol'].nunique()} ตัว รวม {len(evaluated)} การประเมิน "
            f"(ครบ {HORIZON} วัน {int(evaluated['ret'].notna().sum())})",
        ]),
        "## ผลตรวจ look-ahead",
        f"poison check ผ่าน {len(poisoned)} วัน ({', '.join(f'{t:%Y-%m-%d}' for t in poisoned)}): "
        f"ข้อมูลหลังวันที่ทดสอบ ×{POISON_FACTOR} แล้วผลประเมินไม่เปลี่ยน excess ของ MoS ที่สลับแบบสุ่ม (แถว \"สลับ MoS\" เฉลี่ย {PLACEBO_SEEDS} รอบ) ควรใกล้ 0",
        "## ผลรวม",
        "hit = High สูงสุดใน 63 วันถึง fair value นับเฉพาะ MoS > 0 (candidate: นับทุกตัวเทียบ fair value ของ gate, "
        "candidate (median) และ relative: เทียบ median fair value) "
        "excess = ผลตอบแทนรวมปันผลของกลุ่ม MoS ≥ เกณฑ์ − ค่าเฉลี่ยของหุ้นทุกตัวที่ประเมินได้ในวันเดียวกัน คิดต่อวันที่แล้วสรุปข้ามวัน",
        f"95% CI = ช่วงความเชื่อมั่นของ excess เฉลี่ย จากการสุ่มวันที่ใส่คืน {BOOTSTRAP:,} รอบ, "
        "t = excess เฉลี่ย ÷ standard error ของ excess ต่อวันที่",
        _table(SUMMARY_HEADER, _summary_rows(result["summary"])),
        "## ผลรวมแบบไม่นับค่าผิดปกติ",
        f"ตัดการประเมินที่ MoS < {ABNORMAL_MOS:.0%} หรือ fair value > {ABNORMAL_FV_TO_PRICE:g}× ราคา ออกจากกลุ่ม "
        "baseline ยังเป็นหุ้นทุกตัวที่ประเมินได้",
        _table(SUMMARY_HEADER, _summary_rows(result["clean"])),
        "## ต่อระยะวัดผล",
        f"excess ของกลุ่มที่ {', '.join(str(h) for h in HORIZONS)} วันทำการ baseline คิดใหม่ต่อระยะ "
        f"วันที่ที่ยังไม่ครบระยะไม่ถูกนับ {HORIZON} วันเป็นตัววัดหลัก",
        _table(["กลุ่ม", "วันทำการ", "วันที่", "excess เฉลี่ย", "95% CI", "t"], horizon_rows),
        "## แยกตาม bucket ของ MoS",
        _table(["กลุ่ม", "MoS", "n", "hit", "median ผลตอบแทน", "median excess"]
               + [f"median excess {h} วัน" for h in longer], bucket_rows),
        "## ต่อวันที่ทดสอบ",
        "จำนวนที่คำนวณได้ต่อ method (วันที่ช่วงต้นมีจุดใน band น้อยกว่า 20)",
        _table(["วันที่", "ประเมิน", "ข้าม (cap ขาด)", "candidate", "baseline"] + methods
               + ["candidate %", "candidate (median)", "candidate (median) %", "relative", "relative %"], per_date),
        f"## หุ้นที่ตัด ({len(excluded)} ตัว, {share:.0%})",
        ", ".join(f"{k} {v} ตัว" for k, v in by_reason.items()),
        _table(["หุ้น", "เหตุผล"], [[k, v] for k, v in sorted(excluded.items())]) if excluded else "ไม่มี",
        f"## ค่าประเมินผิดปกติ ({len(odd_rows)} การประเมิน ยังนับในตัววัดทุกตัว)",
        f"MoS < {ABNORMAL_MOS:.0%} หรือ fair value > {ABNORMAL_FV_TO_PRICE:g}× ราคา",
        _table(["วันที่", "หุ้น", "method", "ราคา", "fair value", "MoS"], odd_rows) if odd_rows else "ไม่มี",
        f"## หุ้นที่ดึงข้อมูลไม่ได้ ({len(failures)} ตัว)",
        _table(["หุ้น", "เหตุผล"], [[k, v] for k, v in sorted(failures.items())]) if failures else "ไม่มี",
        "## ข้อจำกัด",
        "\n".join(f"- {x}" for x in LIMITATIONS),
    ]
    return "\n\n".join(parts) + "\n"
