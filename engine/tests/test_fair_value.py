import pandas as pd
import pytest

from shortlist.config import load_config
from shortlist.core import fair_value
from tests.fakes import market_caps

CFG = load_config().fair_value


SHARES = 1e9


def history(n: int = 20, eps: float = 1.0, close: float = 15.0, bvps: float = 10.0, dy: float | None = 0.04):
    return pd.DataFrame(
        {"eps": [eps] * n, "net_profit": [eps * SHARES] * n, "close": [close] * n, "bvps": [bvps] * n,
         "dividend_yield": [dy] * n, "equity": [1e10] * n},
        index=[f"q{i}" for i in range(n)],
    )


def evaluate(q: pd.DataFrame, price: float, peer_pes: list[float], cfg=CFG, caps: pd.DataFrame | None = None) -> dict:
    """Defaults to market caps that match the quarterly close with a constant share count."""
    return fair_value.evaluate(q, price, peer_pes, cfg, market_caps(q) if caps is None else caps)


def item(result: dict, method: str) -> dict:
    return next(i for i in result["items"] if i["method"] == method)


def test_all_methods_computed():
    # EPS TTM 4, PE history 15/4 = 3.75, PBV 1.5, yield 4% -> DPS 0.6
    r = evaluate(history(), price=12.0, peer_pes=[4.0, 5.0, 6.0], cfg=CFG)
    assert [i["method"] for i in r["items"]] == CFG.enabled
    assert item(r, "pe_median")["fair_value"] == pytest.approx(15.0)
    assert item(r, "pe_minus_1sd")["fair_value"] == pytest.approx(15.0)  # no variance
    assert item(r, "pbv_median")["fair_value"] == pytest.approx(15.0)
    assert item(r, "dividend_yield_median")["fair_value"] == pytest.approx(15.0)
    assert item(r, "peer_pe")["fair_value"] == pytest.approx(20.0)
    assert all(i["fair_value"] is not None for i in r["items"])


def test_outlier_pe_is_excluded_from_band():
    # one quarter's close of 1600 over EPS TTM 4 gives PE 400
    q = history()
    q.iloc[10, q.columns.get_loc("close")] = 1600.0
    r = evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    assert item(r, "pe_minus_1sd")["fair_value"] == pytest.approx(15.0)

    uncapped = evaluate(q, price=12.0, peer_pes=[], cfg=CFG.model_copy(update={"max_pe": 1e9}))
    assert item(uncapped, "pe_minus_1sd")["fair_value"] is None  # SD swamps the median


def test_bands_use_median():
    q = history()
    q.iloc[-1, q.columns.get_loc("bvps")] = 10.0
    q.iloc[:5, q.columns.get_loc("close")] = 60.0  # 5 of 20 quarters at PBV 6, median stays 1.5
    r = evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    assert item(r, "pbv_median")["fair_value"] == pytest.approx(15.0)


def test_disabled_method_is_not_shown_or_summarized():
    cfg = CFG.model_copy(update={"enabled": ["pe_median", "pbv_median"]})
    r = evaluate(history(dy=0.20), price=12.0, peer_pes=[], cfg=cfg)
    assert [i["method"] for i in r["items"]] == ["pe_median", "pbv_median"]
    assert r["summary"]["computed"] == 2


def test_mos_per_method():
    # PE band fair value 15.20 vs price 12.40 -> about +18%
    q = history(close=15.2)
    r = evaluate(q, price=12.4, peer_pes=[], cfg=CFG)
    assert item(r, "pe_median")["mos"] == pytest.approx(0.184, abs=0.001)


def test_negative_profit_ttm_makes_pe_methods_na():
    q = history(eps=-0.5)
    r = evaluate(q, price=12.0, peer_pes=[4.0, 5.0, 6.0], cfg=CFG)
    for method in ("pe_median", "pe_minus_1sd", "peer_pe"):
        assert item(r, method)["fair_value"] is None
        assert item(r, method)["reason"] == "กำไร 4 ไตรมาสติดลบ"
    assert r["summary"]["computed"] == 2


def test_no_dividend_makes_yield_band_na():
    r = evaluate(history(dy=None), price=12.0, peer_pes=[], cfg=CFG)
    i = item(r, "dividend_yield_median")
    assert i["fair_value"] is None and i["reason"]



def test_justified_pbv_from_roe_ttm():
    # equity 10.00 a share, profit 4 x 0.425 = ROE TTM 17% -> (0.17 - 0.03) / (0.10 - 0.03) = PBV 2
    r = evaluate(history(eps=0.425), price=12.0, peer_pes=[], cfg=CFG)
    assert item(r, "justified_pbv")["fair_value"] == pytest.approx(20.0)


def test_justified_pbv_na_when_roe_not_above_growth():
    i = item(evaluate(history(eps=0.05), price=12.0, peer_pes=[], cfg=CFG), "justified_pbv")  # ROE TTM 2%
    assert i["fair_value"] is None
    assert "ไม่สูงกว่า g" in i["reason"]


def test_justified_pbv_applies_to_financials():
    # no sector check: a bank at ROE TTM 12% -> (0.12 - 0.03) / 0.07 x 10
    r = evaluate(history(eps=0.3), price=12.0, peer_pes=[], cfg=CFG)
    assert item(r, "justified_pbv")["fair_value"] == pytest.approx(12.86)

def with_yields(yields: list[float], dps_now: float, n: int = 20) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trailing cash yields per quarter (oldest first) and today's trailing DPS."""
    q = history(n=n)
    caps = market_caps(q)
    caps["dividend_yield_ttm"] = yields
    caps.iloc[-1, caps.columns.get_loc("dps_ttm")] = dps_now
    return q, caps


def test_band_divides_current_cash_dps_by_median_trailing_yield():
    q, caps = with_yields([0.05] * 20, dps_now=2.8)
    r = evaluate(q, price=40.0, peer_pes=[], caps=caps)
    assert item(r, "dividend_yield_median")["fair_value"] == pytest.approx(56.0)


def test_quarters_below_the_cash_floor_are_left_out():
    # DITTO: 7 quarters of tiny cash next to stock dividends, then 10 quarters of real cash payouts
    real = [0.011, 0.017, 0.013, 0.015, 0.021, 0.026, 0.018, 0.046, 0.040, 0.036]
    q, caps = with_yields([0.0, 0.0, 0.0] + [0.0002, 0.0001, 0.0001, 0.0003, 0.0004, 0.0003, 0.0004] + real, dps_now=0.5)
    r = evaluate(q, price=12.4, peer_pes=[], caps=caps)
    assert item(r, "dividend_yield_median")["fair_value"] == pytest.approx(0.5 / pd.Series(real).median(), rel=1e-3)


def test_stock_dividends_every_year_make_band_na():
    # DOHOME: cash part never reaches the floor
    q, caps = with_yields([0.0013] * 20, dps_now=0.0044)
    i = item(evaluate(q, price=3.5, peer_pes=[], caps=caps), "dividend_yield_median")
    assert i["fair_value"] is None and i["reason"] == "ไม่มีไตรมาสที่จ่ายปันผลเงินสดถึงเกณฑ์ 0.5%"


def test_stopped_paying_makes_band_na():
    q, caps = with_yields([0.0] * 8 + [0.04] * 12, dps_now=0.0)
    caps.iloc[-4:, caps.columns.get_loc("dividend_yield_ttm")] = 0.0
    i = item(evaluate(q, price=12.0, peer_pes=[], caps=caps), "dividend_yield_median")
    assert i["fair_value"] is None and i["reason"] == "ไม่ได้จ่ายปันผลเงินสดใน 12 เดือนล่าสุด"


def test_too_few_paying_quarters_is_na():
    # SKY: only 3 quarters with a real cash yield in 5 years
    q, caps = with_yields([0.0] * 17 + [0.021] * 3, dps_now=0.37)
    i = item(evaluate(q, price=17.4, peer_pes=[], caps=caps), "dividend_yield_median")
    assert i["fair_value"] is None and "3 ไตรมาส" in i["reason"]


def test_yield_band_does_not_depend_on_statement_coverage():
    # 3BBIF: statements stop 5 quarters back, but yfinance has a cash yield for every quarter
    q, caps = with_yields([0.05] * 20, dps_now=2.8)
    q.iloc[-5:, q.columns.get_loc("eps")] = None
    q.iloc[:12, q.columns.get_loc("eps")] = None
    r = evaluate(q, price=40.0, peer_pes=[], caps=caps)
    assert item(r, "dividend_yield_median")["fair_value"] == pytest.approx(56.0)


def test_merger_flags_structure_change():
    # GULF: equity jumped 173% in one quarter after the merger
    q = history()
    q.iloc[12:, q.columns.get_loc("equity")] = 2.73e10
    r = evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    sc = r["structure_change"]
    assert sc["flag"] and "173%" in sc["reason"] and "q12" in sc["reason"]


def test_par_split_does_not_flag():
    # equity barely moves on a split; share count is deliberately ignored
    q = history()
    q.iloc[12:, q.columns.get_loc("equity")] = 1.12e10
    r = evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    assert not r["structure_change"]["flag"]


def test_fewer_than_three_peers_is_na():
    r = evaluate(history(), price=12.0, peer_pes=[4.0, 5.0], cfg=CFG)
    assert item(r, "peer_pe")["fair_value"] is None
    assert "น้อยกว่า 3" in item(r, "peer_pe")["reason"]


def summary(mos_by_method: dict[str, float]) -> dict:
    return fair_value.summarize(
        [{"method": m, "fair_value": 10.0 + i, "mos": mos} for i, (m, mos) in enumerate(mos_by_method.items())]
    )


def test_summary_counts_undervalued():
    s = summary({"pe_median": 0.2, "pbv_median": 0.1, "dividend_yield_median": 0.05, "justified_pbv": 0.3, "peer_pe": -0.1})
    assert s["label"] == "4/5 undervalued"
    assert (s["min_mos"], s["median_mos"], s["max_mos"]) == (-0.1, 0.1, 0.3)


def test_summary_counts_pe_band_as_one_view():
    s = summary({"pe_median": 0.2, "pe_minus_1sd": 0.1, "pbv_median": 0.1, "dividend_yield_median": 0.05,
                 "justified_pbv": 0.3, "peer_pe": -0.1})
    assert s["label"] == "4/5 undervalued"
    assert (s["min_mos"], s["median_mos"], s["max_mos"]) == (-0.1, 0.1, 0.3)  # from all 6 methods


def test_pe_lines_that_disagree_count_by_average():
    assert summary({"pe_median": 0.2, "pe_minus_1sd": -0.1})["label"] == "1/1 undervalued"  # average +5%


def test_pe_minus_1sd_alone_is_the_pe_view():
    assert summary({"pe_minus_1sd": 0.08, "peer_pe": -0.1})["label"] == "1/2 undervalued"


def test_peers_exclude_self_and_other_sectors():
    pes = {"A": ("Banking", 8.0), "B": ("Banking", None), "C": ("Commerce", 20.0), "D": ("Banking", 10.0)}
    assert fair_value.peers_for("A", "Banking", pes) == [10.0]


def test_par_split_leaves_bands_unchanged():
    # SCAP: source halves old prices and EPS but not BVPS; company-level values don't move
    q = history()
    q.iloc[:10, q.columns.get_loc("close")] = 7.5
    q.iloc[:10, q.columns.get_loc("eps")] = 0.5
    r = evaluate(q, price=12.0, peer_pes=[], caps=market_caps(history()))
    assert item(r, "pe_median")["fair_value"] == pytest.approx(15.0)
    assert item(r, "pbv_median")["fair_value"] == pytest.approx(15.0)


def test_capital_raise_uses_shares_after_raise():
    # 20% more shares at the same company value -> fair value per share falls by 1/1.2
    caps = market_caps(history())
    caps.iloc[-1, caps.columns.get_loc("shares")] = 1.2 * SHARES
    r = evaluate(history(), price=12.0, peer_pes=[3.75, 3.75, 3.75], caps=caps)
    for method in ("pe_median", "pbv_median", "peer_pe"):
        assert item(r, method)["fair_value"] == pytest.approx(12.5)


def test_dividend_adjusted_source_close_is_ignored():
    # PTT 2021Q1: source close 32.29, traded close 41.00; PE uses the market cap from 41.00
    q = history(close=41.0)
    caps = market_caps(q)
    q["close"] = 32.29
    r = evaluate(q, price=30.0, peer_pes=[], caps=caps)
    assert item(r, "pe_median")["fair_value"] == pytest.approx(41.0)


def test_missing_market_caps_are_skipped_and_flagged():
    # WSOL: no share count before the rename, so only 6 of 20 quarters have a market cap
    q = history()
    caps = market_caps(q)
    caps.iloc[:14, caps.columns.get_loc("mkt_cap")] = float("nan")
    r = evaluate(q, price=12.0, peer_pes=[], caps=caps)
    assert item(r, "pe_median")["fair_value"] == pytest.approx(15.0)
    gap = r["history_gap"]
    assert gap["flag"] and "6/20" in gap["reason"]
    assert not evaluate(q, price=12.0, peer_pes=[])["history_gap"]["flag"]


def test_no_market_cap_at_all_is_na():
    caps = market_caps(history())
    caps["mkt_cap"] = float("nan")
    r = evaluate(history(), price=12.0, peer_pes=[], caps=caps)
    for method in ("pe_median", "pe_minus_1sd", "pbv_median"):
        assert item(r, method)["fair_value"] is None
        assert item(r, method)["reason"] == "ไม่มี market cap ย้อนหลัง"


def fv_item(method, value, mos, reason=None):
    return {"method": method, "label": fair_value.LABELS[method], "fair_value": value, "mos": mos, "reason": reason}


GATE = ["peer_pe", "justified_pbv"]


def test_gate_takes_the_lower_gate_method():
    items = [fv_item("pe_median", 30.0, 0.5), fv_item("peer_pe", 15.0, 0.2), fv_item("justified_pbv", 14.2, 0.155)]
    g = fair_value.gate(items, GATE)
    assert (g["mos"], g["fair_value"], g["method"]) == (0.155, 14.2, "justified_pbv")
    assert [r["method"] for r in g["items"]] == GATE


def test_gate_with_one_computable_method():
    items = [fv_item("peer_pe", 15.0, 0.12), fv_item("justified_pbv", None, None, "ROE TTM 2.0% ไม่สูงกว่า g 3.0%")]
    g = fair_value.gate(items, GATE)
    assert (g["mos"], g["fair_value"], g["method"]) == (0.12, 15.0, "peer_pe")


def test_gate_without_computable_method_keeps_each_reason():
    items = [fv_item("pe_median", 30.0, 0.4), fv_item("peer_pe", None, None, "กำไร 4 ไตรมาสติดลบ"),
             fv_item("justified_pbv", None, None, "คำนวณ ROE TTM ไม่ได้")]
    g = fair_value.gate(items, GATE)
    assert (g["mos"], g["fair_value"], g["method"]) == (None, None, None)
    assert [r["reason"] for r in g["items"]] == ["กำไร 4 ไตรมาสติดลบ", "คำนวณ ROE TTM ไม่ได้"]


def test_gate_method_disabled_in_panel_counts_as_not_computable():
    g = fair_value.gate([fv_item("justified_pbv", 14.2, 0.155)], GATE)
    assert g["items"][0]["mos"] is None and g["items"][0]["reason"] == "ปิดเกณฑ์นี้อยู่"
    assert g["method"] == "justified_pbv"
