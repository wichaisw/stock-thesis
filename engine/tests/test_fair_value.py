import pandas as pd
import pytest

from shortlist.config import load_config
from shortlist.core import fair_value

CFG = load_config().fair_value


def history(n: int = 20, eps: float = 1.0, close: float = 15.0, bvps: float = 10.0, dy: float | None = 0.04):
    return pd.DataFrame(
        {"eps": [eps] * n, "close": [close] * n, "bvps": [bvps] * n, "dividend_yield": [dy] * n, "equity": [1e10] * n},
        index=[f"q{i}" for i in range(n)],
    )


def item(result: dict, method: str) -> dict:
    return next(i for i in result["items"] if i["method"] == method)


def test_all_five_methods_computed():
    # EPS TTM 4, PE history 15/4 = 3.75, PBV 1.5, yield 4% -> DPS 0.6
    r = fair_value.evaluate(history(), price=12.0, peer_pes=[4.0, 5.0, 6.0], cfg=CFG)
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
    r = fair_value.evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    assert item(r, "pe_minus_1sd")["fair_value"] == pytest.approx(15.0)

    uncapped = fair_value.evaluate(q, price=12.0, peer_pes=[], cfg=CFG.model_copy(update={"max_pe": 1e9}))
    assert item(uncapped, "pe_minus_1sd")["fair_value"] is None  # SD swamps the median


def test_bands_use_median():
    q = history()
    q.iloc[-1, q.columns.get_loc("bvps")] = 10.0
    q.iloc[:5, q.columns.get_loc("close")] = 60.0  # 5 of 20 quarters at PBV 6, median stays 1.5
    r = fair_value.evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    assert item(r, "pbv_median")["fair_value"] == pytest.approx(15.0)


def test_disabled_method_is_not_shown_or_summarized():
    cfg = CFG.model_copy(update={"enabled": ["pe_median", "pbv_median"]})
    r = fair_value.evaluate(history(dy=0.20), price=12.0, peer_pes=[], cfg=cfg)
    assert [i["method"] for i in r["items"]] == ["pe_median", "pbv_median"]
    assert r["summary"]["computed"] == 2


def test_mos_per_method():
    # PE band fair value 15.20 vs price 12.40 -> about +18%
    q = history(close=15.2)
    r = fair_value.evaluate(q, price=12.4, peer_pes=[], cfg=CFG)
    assert item(r, "pe_median")["mos"] == pytest.approx(0.184, abs=0.001)


def test_negative_eps_ttm_makes_pe_methods_na():
    q = history(eps=-0.5)
    r = fair_value.evaluate(q, price=12.0, peer_pes=[4.0, 5.0, 6.0], cfg=CFG)
    for method in ("pe_median", "pe_minus_1sd", "peer_pe"):
        assert item(r, method)["fair_value"] is None
        assert item(r, method)["reason"] == "EPS TTM ติดลบ"
    assert r["summary"]["computed"] == 2


def test_no_dividend_makes_yield_band_na():
    r = fair_value.evaluate(history(dy=None), price=12.0, peer_pes=[], cfg=CFG)
    i = item(r, "dividend_yield_median")
    assert i["fair_value"] is None and i["reason"]


def test_too_few_dividend_quarters_is_na():
    # SKY: only 3 tiny-or-recent yields in 5 years made the median ~0 and fair value 1,533 baht
    q = history(dy=None)
    q["dividend_yield"] = q["dividend_yield"].astype(float)
    q.iloc[[0, 1, -1], q.columns.get_loc("dividend_yield")] = [0.0001, 0.0002, 0.021]
    r = fair_value.evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    i = item(r, "dividend_yield_median")
    assert i["fair_value"] is None and "3 ไตรมาส" in i["reason"]


def test_dividend_paid_earlier_in_the_year_still_counts():
    # GLOBAL: yield shows 0 in the two quarters after the payout
    q = history(dy=0.04)
    q.iloc[-2:, q.columns.get_loc("dividend_yield")] = 0.0
    r = fair_value.evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    assert item(r, "dividend_yield_median")["fair_value"] == pytest.approx(15.0)


def test_merger_flags_structure_change():
    # GULF: equity jumped 173% in one quarter after the merger
    q = history()
    q.iloc[12:, q.columns.get_loc("equity")] = 2.73e10
    r = fair_value.evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    sc = r["structure_change"]
    assert sc["flag"] and "173%" in sc["reason"] and "q12" in sc["reason"]


def test_par_split_does_not_flag():
    # equity barely moves on a split; share count is deliberately ignored
    q = history()
    q.iloc[12:, q.columns.get_loc("equity")] = 1.12e10
    r = fair_value.evaluate(q, price=12.0, peer_pes=[], cfg=CFG)
    assert not r["structure_change"]["flag"]


def test_fewer_than_three_peers_is_na():
    r = fair_value.evaluate(history(), price=12.0, peer_pes=[4.0, 5.0], cfg=CFG)
    assert item(r, "peer_pe")["fair_value"] is None
    assert "น้อยกว่า 3" in item(r, "peer_pe")["reason"]


def test_summary_counts_undervalued():
    items = [{"fair_value": 10.0 + i, "mos": m} for i, m in enumerate([0.2, 0.1, 0.05, 0.3, -0.1])]
    s = fair_value.summarize(items)
    assert s["label"] == "4/5 undervalued"
    assert (s["min_mos"], s["median_mos"], s["max_mos"]) == (-0.1, 0.1, 0.3)


def test_peers_exclude_self_and_other_sectors():
    pes = {"A": ("Banking", 8.0), "B": ("Banking", None), "C": ("Commerce", 20.0), "D": ("Banking", 10.0)}
    assert fair_value.peers_for("A", "Banking", pes) == [10.0]
