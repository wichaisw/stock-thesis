import numpy as np
import pandas as pd
import pytest

from shortlist import backtest as bt
from shortlist.config import load_config
from shortlist.sources import QUARTERLY_COLUMNS, StockInfo
from tests.fakes import market_caps

CFG = load_config()
T = pd.Timestamp("2023-03-31")


def quarters(start: str = "2017Q1", end: str = "2024Q4", **overrides) -> pd.DataFrame:
    values = {"eps": 1.0, "net_profit": 1e9, "net_profit_yoy": 0.05, "equity": 1e10, "de": 0.8, "ocf": 5e8,
              "npm": 0.10, "bvps": 10.0, "dividend_yield": 0.04, "close": 15.0} | overrides
    idx = [str(p) for p in pd.period_range(start, end, freq="Q")]
    return pd.DataFrame({c: [values[c]] * len(idx) for c in QUARTERLY_COLUMNS}, index=idx)


def prices(close: float = 12.0, volume: float = 5_000_000.0, start: str = "2020-01-01", end: str = "2024-12-31"):
    idx = pd.bdate_range(start, end)
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": volume, "adj_close": close}, index=idx
    )


def stock(symbol: str = "AAA", sector: str = "Food", q: pd.DataFrame | None = None, p: pd.DataFrame | None = None,
          splits: pd.Series | None = None, caps: pd.DataFrame | None = None) -> bt.StockData:
    q = quarters() if q is None else q
    p = prices() if p is None else p
    return bt.StockData(
        info=StockInfo(symbol, symbol, sector, "SET"),
        prices=p,
        splits=pd.Series(0.0, index=p.index) if splits is None else splits,
        quarterly=q,
        caps=market_caps(q) if caps is None else caps,
    )


# 1.1 excluded stocks


def test_split_or_stock_dividend_excludes_the_stock():
    p = prices()
    splits = pd.Series(0.0, index=p.index)
    splits[pd.Timestamp("2022-05-10")] = 1.1  # stock dividend 10:1, which yfinance records as a split
    out = bt.excluded({"AAA": stock(p=p, splits=splits), "BBB": stock("BBB")}, "2021Q1", "2026Q2", 0.5)
    assert out == {"AAA": "split หรือปันผลเป็นหุ้น 2022-05-10 ratio 1.1"}


def test_merger_inside_the_range_excludes_the_stock():
    q = quarters(end="2025Q4")
    q.loc["2025Q2":, "equity"] = 1e10 * 2.73  # +173%, like GULF 2Q25
    out = bt.excluded({"GULF": stock("GULF", q=q)}, "2021Q1", "2026Q2", 0.5)
    assert out == {"GULF": "ส่วนผู้ถือหุ้นเปลี่ยน 173% ใน 2025Q2"}


def test_merger_before_the_range_is_kept():
    q = quarters()
    q.loc["2019Q1":, "equity"] = 1e10 * 2.73
    assert bt.excluded({"AAA": stock(q=q)}, "2021Q1", "2026Q2", 0.5) == {}


# 1.2 data as known at T


def test_statement_not_yet_due_is_not_used():
    s = bt.cut(stock(), T, CFG.catalyst)
    assert s.quarterly.index[-1] == "2022Q4"  # due 1 Mar 2023; 2023Q1 is due 15 May
    assert bt.cut(stock(), pd.Timestamp("2023-05-15"), CFG.catalyst).quarterly.index[-1] == "2023Q1"


def test_prices_and_caps_stop_at_t():
    s = bt.cut(stock(), T, CFG.catalyst)
    assert s.prices.index.max() <= T
    assert s.caps.index[-1] == "2023Q1"


def test_stock_without_statements_keeps_its_columns():
    empty = quarters().iloc[0:0]  # thaifin with no EPS at all, like SCL and TFFIF
    s = bt.cut(stock(q=empty, caps=market_caps(quarters())), T, CFG.catalyst)
    assert list(s.quarterly.columns) == list(QUARTERLY_COLUMNS)
    rows, _ = bt.evaluate_date({"AAA": stock(), "SCL": stock("SCL", q=empty, caps=market_caps(quarters()))}, T, CFG)
    assert "AAA" in {r["symbol"] for r in rows}


def test_prices_after_t_do_not_change_the_evaluation():
    p = prices()
    p.loc[p.index > T, ["close", "high", "volume"]] = [999.0, 999.0, 1.0]
    rows, _ = bt.evaluate_date({"AAA": stock(p=p)}, T, CFG)
    assert rows == bt.evaluate_date({"AAA": stock()}, T, CFG)[0]
    assert {r["price"] for r in rows} == {12.0}


# 1.3 one test date


def test_illiquid_at_t_is_not_evaluated_even_if_liquid_today():
    p = prices(volume=100.0)
    p.loc[p.index > T, "volume"] = 5_000_000.0
    rows, _ = bt.evaluate_date({"AAA": stock(), "THIN": stock("THIN", p=p)}, T, CFG)
    assert {r["symbol"] for r in rows} == {"AAA"}


def test_cap_gap_in_the_middle_skips_only_that_date():
    q = quarters()
    caps = market_caps(q)
    caps.loc["2020Q2", "mkt_cap"] = np.nan
    s = {"AAA": stock(q=q, caps=caps)}
    rows, skipped = bt.evaluate_date(s, T, CFG)
    assert rows == [] and skipped == {"AAA": "market cap ขาดใน 2020Q2"}
    # 20 quarters back from 2025Q4's lookback no longer reach 2020Q2
    later = pd.Timestamp("2025-12-31")
    s = {"AAA": stock(q=quarters(end="2025Q4"), p=prices(end="2026-03-31"),
                      caps=market_caps(quarters(end="2025Q4")).assign(
                          mkt_cap=lambda c: c["mkt_cap"].where(c.index != "2020Q2")))}
    rows, skipped = bt.evaluate_date(s, later, CFG)
    assert rows and skipped == {}


def test_caps_starting_late_is_not_a_gap():
    q = quarters()
    caps = market_caps(q)
    caps.loc[:"2018Q3", ["mkt_cap", "shares"]] = np.nan  # share counts start Nov 2018
    rows, skipped = bt.evaluate_date({"AAA": stock(q=q, caps=caps)}, T, CFG)
    assert skipped == {} and rows


def test_method_without_value_is_a_row_with_none():
    rows, _ = bt.evaluate_date({"AAA": stock()}, T, CFG)
    peer = next(r for r in rows if r["method"] == "peer_pe")
    assert peer["fair_value"] is None and peer["mos"] is None  # no peers in the sector
    assert {r["method"] for r in rows} == set(CFG.fair_value.enabled) | {bt.MEDIAN, bt.GATE}


def test_abnormal_value_is_flagged_and_kept():
    rows, _ = bt.evaluate_date({"AAA": stock(p=prices(close=2.0, volume=1e8))}, T, CFG)
    pe = next(r for r in rows if r["method"] == "pe_median")
    assert pe["fair_value"] == pytest.approx(15.0) and pe["abnormal"]  # 7.5× price


def test_candidate_needs_quality_and_median_mos():
    rows, _ = bt.evaluate_date({"AAA": stock()}, T, CFG)
    med = next(r for r in rows if r["method"] == bt.MEDIAN)
    assert med["quality_passed"] and med["mos"] >= 0.10 and med["candidate_median"]


def test_candidate_reads_the_gate_row():
    rows, _ = bt.evaluate_date({"AAA": stock()}, T, CFG)
    by = {r["method"]: r for r in rows}
    gate_items = [by[m] for m in CFG.candidates.gate_methods if by[m]["mos"] is not None]
    assert gate_items  # justified_pbv is computable; peer_pe has no peers
    assert by[bt.GATE]["mos"] == min(r["mos"] for r in gate_items)
    assert by[bt.GATE]["candidate"] == (by[bt.GATE]["mos"] >= CFG.candidates.min_gate_mos)


# validate-gate-variants: variant rules (MoS of the computable gate methods)


def test_option_a_passes_with_one_method_slightly_negative():
    assert bt.option_a([0.20, -0.05]) and not bt.at_least(0.10)([0.20, -0.05])


def test_option_a_with_one_method_needs_12_percent():
    assert not bt.option_a([0.11]) and bt.at_least(0.10)([0.11])
    assert bt.option_a([0.12])


def test_option_b_needs_both_methods():
    assert not bt.option_b([0.30])


def test_option_b_rejects_a_method_far_below_zero_even_if_the_mean_passes():
    assert not bt.option_b([0.40, -0.20])
    assert bt.option_b([0.20, -0.04])


def test_no_computable_gate_method_passes_no_rule():
    assert not any(rule([]) for rule in (bt.at_least(0.10), bt.option_a, bt.option_b))


def gate_row(q: pd.DataFrame) -> dict:
    rows, _ = bt.evaluate_date({"AAA": stock(q=q)}, T, CFG)
    return next(r for r in rows if r["method"] == bt.GATE)


def test_all_pass_variant_drops_a_stock_failing_one_check():
    q = quarters()
    q.loc["2022Q4", "ocf"] = -1e8
    q.loc["2022Q3", "ocf"] = -1e8  # 2 of the last 4 known at T are negative: OCF fails, the other checks pass
    r = gate_row(q)
    assert r["quality_passed"] and r["candidate"]
    assert not r["v_all_pass"] and not r["v_all_pass_de2"]


def test_de_2_variant_keeps_de_1_8():
    r = gate_row(quarters(de=1.8))
    assert r["candidate"] and r["v_all_pass_de2"] and not r["v_all_pass"]


def test_variants_are_scored_like_candidate():
    df = known_rows()
    df["v_mos15"] = df["candidate"]
    s = bt.metrics(df, 0.10)["summary"].set_index("group")
    cols = ["excess_mean", "excess_dates", "hit_rate", "hit_n", "excess_t"]
    assert s.loc["candidate MoS ≥ 15%", cols].tolist() == s.loc[bt.CANDIDATE, cols].tolist()


# 1.4 metrics


def test_outcome_reads_63_trading_days_after_t():
    p = prices(start="2023-01-02", end="2023-12-29")
    after = p.index[p.index > T]
    p.loc[after[62], "adj_close"] = 18.0  # 63rd trading day: +50%
    p.loc[after[63], "high"] = 99.0  # 64th day: outside the window
    p.loc[after[10], "high"] = 14.0
    assert bt.outcome(p, T) == (pytest.approx(0.5), 14.0)
    assert bt.outcome(p, pd.Timestamp("2023-12-01")) is None  # horizon not passed yet


def frame(rows: list[tuple], **extra) -> pd.DataFrame:
    """(date, symbol, method, mos, fair_value, ret, max_high, candidate); `extra` overrides the other columns."""
    cols = ["date", "symbol", "method", "mos", "fair_value", "ret", "max_high", "candidate"]
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    defaults = {"ret_126": None, "ret_252": None, "abnormal": False, "quality_passed": True, "relative": False,
                "candidate_median": False} | {v.flag: False for v in bt.VARIANTS}
    for col, value in (defaults | extra).items():
        df[col] = value
    return df


def known_rows() -> pd.DataFrame:
    rows = []
    # day 1: baseline (mean of median rows) = (0.20 + 0.00) / 2 = 0.10
    # day 2: baseline = (0.00 + 0.10) / 2 = 0.05
    for d, sym, mos, ret, high, cand in [
        ("2023-03-31", "A", 0.40, 0.20, 15.0, True),
        ("2023-03-31", "B", -0.20, 0.00, 10.0, False),
        ("2023-06-30", "A", 0.05, 0.00, 10.0, False),
        ("2023-06-30", "B", 0.20, 0.10, 11.0, True),
    ]:
        fv = 10 / (1 - mos)  # price 10
        rows += [(d, sym, m, mos, fv, ret, high, cand) for m in ("pe_median", bt.MEDIAN, bt.GATE)]
    rows.append(("2023-06-30", "C", "pe_median", None, None, None, None, False))  # horizon not passed
    rows.append(("2023-06-30", "D", "pe_median", None, None, 0.3, 12.0, False))  # method not computable
    df = frame(rows)
    df["candidate_median"] = df["candidate"]  # both rules pick the same stocks unless a test says otherwise
    return df


def test_excess_is_per_date_then_summarized():
    pe = bt.metrics(known_rows(), 0.10)["summary"].set_index("group").loc["pe_median"]
    # day 1: A selected 0.20 − 0.10 = +0.10; day 2: B selected 0.10 − 0.05 = +0.05
    assert pe["excess_dates"] == 2
    assert pe["excess_mean"] == pytest.approx(0.075)
    assert pe["excess_positive"] == 1.0
    assert pe["uncomputed"] == 2  # C and D


def test_hit_rate_counts_only_positive_mos():
    s = bt.metrics(known_rows(), 0.10)["summary"].set_index("group")
    # MoS > 0: A day 1 (fv 16.7, high 15 → miss), A day 2 (fv 10.5, high 10 → miss), B day 2 (fv 12.5, high 11 → miss)
    assert s.loc["pe_median", "hit_n"] == 3 and s.loc["pe_median", "hit_rate"] == 0.0
    assert s.loc[bt.CANDIDATE, "hit_n"] == 2  # candidate flag, not MoS sign


def test_buckets_are_fixed():
    b = bt.metrics(known_rows(), 0.10)["buckets"]
    pe = b[b["group"] == "pe_median"].set_index("bucket")
    assert list(pe.index) == ["< 0", "0–10%", "10–30%", "≥ 30%"]
    assert pe.loc["≥ 30%", "n"] == 1 and pe.loc["≥ 30%", "median_excess"] == pytest.approx(0.10)
    assert pe.loc["< 0", "median_ret"] == pytest.approx(0.0)


def test_placebo_shuffle_is_near_zero_when_selection_is_informative():
    rng = np.random.default_rng(1)
    rows = []
    for d in pd.date_range("2000-03-31", periods=200, freq="QE"):
        for i in range(10):
            mos = 0.3 if i < 5 else -0.1
            ret = (0.1 if i < 5 else 0.0) + rng.normal(0, 0.02)
            rows.append((d, f"S{i}", bt.MEDIAN, mos, 10.0, ret, 10.0, mos > 0))
    s = bt.metrics(frame(rows), 0.10, seed=7)["summary"].set_index("group").loc[bt.MEDIAN]
    assert s["excess_mean"] == pytest.approx(0.05, abs=0.01)
    assert abs(s["placebo_mean"]) < 0.01
    again = bt.metrics(frame(rows), 0.10, seed=7)["summary"].set_index("group").loc[bt.MEDIAN]
    assert again["placebo_mean"] == s["placebo_mean"]  # fixed seed


def test_uncertainty_matches_the_t_formula_and_repeats():
    x = [0.01, 0.03, -0.02, 0.05, 0.00, 0.02]
    u = bt.uncertainty(x)
    se = np.std(x, ddof=1) / np.sqrt(len(x))
    assert u["t"] == pytest.approx(np.mean(x) / se)
    assert u["ci_low"] < np.mean(x) < u["ci_high"]
    assert bt.uncertainty(x) == u  # fixed seed
    assert bt.uncertainty([0.05]) == {"t": None, "ci_low": None, "ci_high": None}


def test_summary_has_t_and_ci_but_placebo_does_not_need_them():
    pe = bt.metrics(known_rows(), 0.10)["summary"].set_index("group").loc["pe_median"]
    assert pe["excess_t"] == pytest.approx(0.075 / (np.std([0.10, 0.05], ddof=1) / np.sqrt(2)))
    assert pe["excess_ci_low"] <= 0.075 <= pe["excess_ci_high"]
    one_date = bt.metrics(known_rows()[lambda d: d["date"] == "2023-03-31"], 0.10)["summary"]
    assert one_date.set_index("group").loc["pe_median", "excess_t"] is None


def test_clean_drops_abnormal_from_the_group_but_not_the_baseline():
    rows = known_rows()
    rows.loc[(rows["symbol"] == "A") & (rows["date"] == "2023-03-31"), "abnormal"] = True  # fv > 5× price
    m = bt.metrics(rows, 0.10)
    assert m["summary"].set_index("group").loc["pe_median", "excess_dates"] == 2
    clean = m["clean"].set_index("group")
    assert clean.loc["pe_median", "excess_dates"] == 1  # A was the only pick on day 1
    assert clean.loc["pe_median", "excess_mean"] == pytest.approx(0.05)  # day 2 against the same baseline 0.05
    assert clean.loc[bt.CANDIDATE, "excess_dates"] == 1  # the gate row of A was abnormal too


def test_each_candidate_group_drops_the_abnormal_row_of_its_own_rule():
    rows = known_rows()
    a_day1 = (rows["symbol"] == "A") & (rows["date"] == "2023-03-31")
    rows.loc[a_day1 & (rows["method"] == bt.GATE), "abnormal"] = True
    clean = bt.metrics(rows, 0.10)["clean"].set_index("group")
    assert clean.loc[bt.CANDIDATE, "excess_dates"] == 1  # A's gate row was the only pick on day 1
    assert clean.loc[bt.CANDIDATE_MEDIAN, "excess_dates"] == 2  # the median row of A is fine
    rows.loc[a_day1, "abnormal"] = False
    rows.loc[a_day1 & (rows["method"] == bt.MEDIAN), "abnormal"] = True
    clean = bt.metrics(rows, 0.10)["clean"].set_index("group")
    assert (clean.loc[bt.CANDIDATE, "excess_dates"], clean.loc[bt.CANDIDATE_MEDIAN, "excess_dates"]) == (2, 1)


def test_candidate_hit_is_measured_against_the_gate_fair_value():
    rows = known_rows()
    rows.loc[rows["method"] == bt.GATE, "fair_value"] = 1.0  # every High reaches it
    s = bt.metrics(rows, 0.10)["summary"].set_index("group")
    assert s.loc[bt.CANDIDATE, "hit_rate"] == 1.0
    assert s.loc[bt.CANDIDATE_MEDIAN, "hit_rate"] == 0.0


def test_longer_horizon_counts_only_dates_that_reached_it():
    rows = known_rows()
    day1 = rows["date"] == "2023-03-31"
    rows.loc[day1, "ret_126"] = rows.loc[day1, "ret"] * 2
    rows.loc[day1, "ret_252"] = rows.loc[day1, "ret"] * 3
    m = bt.metrics(rows, 0.10)
    h = m["horizons"].set_index(["group", "horizon"])
    assert h.loc[("pe_median", 63), "dates"] == 2
    assert h.loc[("pe_median", 252), "dates"] == 1
    assert h.loc[("pe_median", 252), "mean"] == pytest.approx(0.60 - 0.30)  # A 0.60 − baseline (0.60 + 0) / 2
    assert m["summary"].set_index("group").loc["pe_median", "hit_n"] == 3  # hit stays at 63 days
    b = m["buckets"]
    top = b[(b["group"] == "pe_median") & (b["bucket"] == "≥ 30%")].iloc[0]
    assert top["median_excess_252"] == pytest.approx(0.30)
    assert pd.isna(b[(b["group"] == "pe_median") & (b["bucket"] == "0–10%")].iloc[0]["median_excess_252"])


def test_with_outcomes_adds_longer_horizons():
    p = prices(start="2023-01-02", end="2023-12-29")
    after = p.index[p.index > T]
    p.loc[after[125], "adj_close"] = 24.0
    rows = pd.DataFrame([{"date": T, "symbol": "AAA"}])
    out = bt.with_outcomes(rows, {"AAA": p}).iloc[0]
    assert out["ret"] == pytest.approx(0.0) and out["ret_126"] == pytest.approx(1.0)
    assert out["ret_252"] is None  # the year has fewer than 252 trading days after T


def test_top_share_is_relative_and_ignores_missing():
    mos = {f"S{i}": i / 10 - 0.9 for i in range(10)} | {"NONE": None}  # all negative but S9 (0.0)
    assert bt.top_share(mos) == {"S8", "S9"}


def test_relative_needs_quality_and_the_top_rank():
    stocks = {sym: stock(sym, p=prices(close=close)) for sym, close in zip("ABCDE", [8, 10, 12, 14, 16])}
    rows, _ = bt.evaluate_date(stocks, T, CFG)
    med = {r["symbol"]: r for r in rows if r["method"] == bt.MEDIAN}
    top = bt.top_share({k: r["mos"] for k, r in med.items()})
    assert top == {"A"}  # 5 stocks, top 20%: the cheapest
    assert {k for k, r in med.items() if r["relative"]} == {k for k in top if med[k]["quality_passed"]}
    failing = quarters(eps=-1.0, net_profit=-1e9)  # a loss fails quality whatever the MoS
    rows, _ = bt.evaluate_date(stocks | {"LOSS": stock("LOSS", q=failing)}, T, CFG)
    assert not any(r["relative"] for r in rows if r["symbol"] == "LOSS")


def test_relative_group_is_scored_like_candidate():
    rows = known_rows()
    rows.loc[(rows["symbol"] == "B") & (rows["date"] == "2023-03-31"), "relative"] = True
    s = bt.metrics(rows, 0.10)["summary"].set_index("group")
    assert s.loc[bt.RELATIVE, "hit_n"] == 1
    assert s.loc[bt.RELATIVE, "excess_mean"] == pytest.approx(0.00 - 0.10)


# 1.5 poison check


def universe() -> dict[str, bt.StockData]:
    return {sym: stock(sym, q=quarters(eps=1.0 + i / 10, net_profit=(1 + i / 10) * 1e9)) for i, sym in enumerate("ABCD")}


DATES = bt.quarter_ends("2021Q1", "2024Q2")


def test_poison_check_passes_on_clean_cut():
    assert len(bt.poison_check(universe(), DATES, CFG)) == 5


def test_poison_check_catches_a_leaky_cut():
    def leaky(s, t, cfg):
        return bt.replace(bt.cut(s, t, cfg), quarterly=s.quarterly)

    with pytest.raises(bt.LookAhead, match=r"look-ahead: A \d{4}-\d{2}-\d{2} "):
        bt.poison_check(universe(), DATES, CFG, cut=leaky)


def test_poison_check_catches_cutting_by_quarter_end_instead_of_deadline():
    def by_quarter_end(s, t, cfg):
        right = bt.cut(s, t, cfg)
        return bt.replace(right, quarterly=s.quarterly[s.quarterly.index <= str(t.to_period("Q"))])

    with pytest.raises(bt.LookAhead):
        bt.poison_check(universe(), DATES, CFG, cut=by_quarter_end)


# 1.6 markdown


def test_report_has_every_section():
    stocks = universe()
    rows = []
    skipped = {}
    for t in DATES:
        r, skipped[t] = bt.evaluate_date(stocks, t, CFG)
        rows += r
    df = bt.with_outcomes(pd.DataFrame(rows), {k: s.prices for k, s in stocks.items()})
    md = bt.report(
        meta={"run_date": "2026-10-15", "commit": "abc1234", "dirty": True, "cache_date": "2026-10-14"},
        cfg=CFG, dates=DATES, universe=6, excluded={"SCAP": "split หรือปันผลเป็นหุ้น 2022-05-10 ratio 2"},
        failures={"XYZ": "ดึงงบไม่ได้: ValueError"}, skipped=skipped, poisoned=DATES[:5], rows=df,
        result=bt.metrics(df, CFG.candidates.min_gate_mos),
    )
    assert "`abc1234 (มีการแก้ที่ยังไม่ commit)`" in md
    for part in ["วันที่ของ cache: 2026-10-14", "2021-03-31 ถึง 2024-06-30 (14 วัน", "structure_change_threshold",
                 "ตัดออก 1 ตัว (17%)", "## ผลตรวจ look-ahead", "poison check ผ่าน 5 วัน", "(สลับ MoS)",
                 "## แยกตาม bucket ของ MoS", "## ต่อวันที่ทดสอบ", "SCAP", "## ค่าประเมินผิดปกติ", "XYZ",
                 "survivorship bias", "restate", "thaifin อย่างเดียว", "ไม่เป็นอิสระ",
                 "| 95% CI | t |", "## ผลรวมแบบไม่นับค่าผิดปกติ", "## ต่อระยะวัดผล", "median excess 252 วัน",
                 "| candidate % | candidate (median) | candidate (median) % | relative | relative % |", "ช่วงวัดผลของวันที่ทดสอบที่ติดกันซ้อนกัน",
                 "90 ช่วงความเชื่อมั่น", "## variant ของ candidate rule", "ไม่ใช่ out-of-sample", "| ผ่านเกณฑ์ | เหตุผล |",
                 "| candidate Option A |", "| candidate quality ผ่านทุกข้อ + D/E ≤ 2.0 |"]:
        assert part in md, part
    for method in CFG.fair_value.enabled + [bt.MEDIAN, bt.GATE, bt.CANDIDATE, bt.CANDIDATE_MEDIAN, bt.RELATIVE]:
        assert f"| {method} |" in md, method
    assert md.count("| candidate (relative) (สลับ MoS) |") == 2  # summary and clean


# validate-gate-variants: variant table and verdict


def variant_rows(pick) -> pd.DataFrame:
    """16 dates (8 before 2024, 8 from 2024), 10 stocks; stock i returns 0.10 − 0.01·i. candidate = stocks 0–4,
    the MoS ≥ 15% variant = pick(date index, stock index)."""
    dates = list(pd.date_range("2022-03-31", periods=8, freq="QE")) + list(pd.date_range("2024-03-31", periods=8, freq="QE"))
    rows, flags = [], []
    for d_i, d in enumerate(dates):
        for i in range(10):
            ret = 0.10 - 0.01 * i + 0.001 * (d_i % 3)
            for m in (bt.MEDIAN, bt.GATE):
                rows.append((d, f"S{i}", m, 0.2, 10.0, ret, 10.0, i < 5))
                flags.append(bool(pick(d_i, i)))
    df = frame(rows)
    df["v_mos15"] = flags
    return df


def verdict(df: pd.DataFrame) -> pd.Series:
    return bt.metrics(df, 0.10)["verdict"].set_index("group").loc["candidate MoS ≥ 15%"]


def test_variant_that_beats_candidate_everywhere_passes():
    v = verdict(variant_rows(lambda d, i: i < 4))
    assert v["passed"] and v["why"] == ""
    assert v["diff_mean"] == pytest.approx(0.005)


def test_variant_winning_one_half_fails():
    v = verdict(variant_rows(lambda d, i: i < 4 if d < 8 else i >= 6))
    assert not v["passed"] and "ไม่ชนะ candidate ทุกช่วง" in v["why"]


def test_variant_whose_ci_crosses_zero_fails():
    v = verdict(variant_rows(lambda d, i: i < 4 if d % 2 else i >= 6))
    assert not v["passed"] and "95% CI คร่อม 0" in v["why"]


def test_variant_with_too_few_candidates_fails_even_when_it_wins():
    v = verdict(variant_rows(lambda d, i: i == 0))
    assert not v["passed"] and v["why"] == "candidate น้อยเกินไป"
    assert v["mean_candidates"] == 1.0


def test_date_without_variant_candidate_is_not_scored():
    df = variant_rows(lambda d, i: i < 4 and d != 3)
    result = bt.metrics(df, 0.10)
    first = result["periods"].set_index(["group", "period"]).loc[("candidate MoS ≥ 15%", "2022Q1–2023Q4")]
    assert (first["dates"], first["dates_without"]) == (7, 1)
    assert result["verdict"].set_index("group").loc["candidate MoS ≥ 15%", "diff_dates"] == 15


def test_candidate_periods_cover_the_summary_dates():
    result = bt.metrics(variant_rows(lambda d, i: i < 4), 0.10)
    cand = result["periods"][result["periods"]["group"] == bt.CANDIDATE]
    assert cand["period"].tolist() == ["2022Q1–2023Q4", "2024Q1–2025Q4"]
    assert cand["dates"].sum() == result["summary"].set_index("group").loc[bt.CANDIDATE, "excess_dates"]
