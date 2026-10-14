import numpy as np
import pandas as pd
import pytest

from shortlist.config import load_config
from shortlist.core import cdc

CFG = load_config().cdc


def lines_with_gap(gaps: list[float]) -> tuple[pd.Series, pd.Series]:
    """Slow fixed at 100; fast placed so (slow - fast) / slow equals each gap."""
    slow = pd.Series([100.0] * len(gaps))
    return slow * (1 - pd.Series(gaps)), slow


def test_gap_narrowing_gives_speed_and_eta():
    # 5 days ago gap 2%, today 1%
    fast, slow = lines_with_gap([0.03] * 60 + [0.02, 0.018, 0.016, 0.014, 0.012, 0.01])
    r = cdc.classify(fast, slow, CFG)
    assert r["gap_pct"] == pytest.approx(0.01)
    assert r["speed"] == pytest.approx(0.002)
    assert r["eta_days"] == pytest.approx(5)
    assert r["state"] == "bear-approaching"


def test_gap_widening_has_no_eta_and_is_bear_far():
    fast, slow = lines_with_gap([0.01] * 60 + [0.01, 0.012, 0.014, 0.016, 0.018, 0.02])
    r = cdc.classify(fast, slow, CFG)
    assert r["eta_days"] is None
    assert r["state"] == "bear-far"


def test_eta_six_days_is_approaching():
    # today 1.2%, 5 days ago 2.2% -> speed 0.2%/day -> ETA 6
    fast, slow = lines_with_gap([0.03] * 60 + [0.022, 0.02, 0.018, 0.016, 0.014, 0.012])
    r = cdc.classify(fast, slow, CFG)
    assert r["eta_days"] == pytest.approx(6)
    assert r["state"] == "bear-approaching"


def test_eta_beyond_window_is_bear_far():
    fast, slow = lines_with_gap([0.05] * 60 + [0.05, 0.049, 0.048, 0.047, 0.046, 0.045])
    r = cdc.classify(fast, slow, CFG)
    assert r["eta_days"] == pytest.approx(45)
    assert r["state"] == "bear-far"


def test_crossed_two_days_ago_is_just_crossed():
    fast, slow = lines_with_gap([0.02] * 60 + [0.01, -0.005, -0.01, -0.015])
    r = cdc.classify(fast, slow, CFG)
    assert r["days_since_cross"] == 2
    assert r["state"] == "just-crossed"


def test_crossed_long_ago_is_bull():
    fast, slow = lines_with_gap([0.02] * 30 + [-0.01] * 30)
    r = cdc.classify(fast, slow, CFG)
    assert r["days_since_cross"] == 29
    assert r["state"] == "bull"


def test_too_few_days_has_no_state():
    prices = pd.DataFrame({c: np.linspace(10, 12, 30) for c in ["open", "high", "low", "close"]})
    r = cdc.evaluate(prices, CFG)
    assert r["state"] is None
    assert "ข้อมูลราคาไม่พอ" in r["reason"]


def test_lines_follow_cdc_formula():
    prices = pd.DataFrame(
        {"open": [10.0, 11.0, 12.0], "high": [12.0, 13.0, 14.0], "low": [8.0, 9.0, 10.0], "close": [10.0, 11.0, 12.0]}
    )
    df = cdc.lines(prices, CFG)
    src = [10.0, 11.0, 12.0]
    ap = [src[0]]
    for x in src[1:]:
        ap.append(ap[-1] + (2 / 3) * (x - ap[-1]))  # EMA 2 -> alpha 2/3
    assert df["ap"].tolist() == pytest.approx(ap)
    fast = [ap[0]]
    for x in ap[1:]:
        fast.append(fast[-1] + (2 / 13) * (x - fast[-1]))
    assert df["fast"].tolist() == pytest.approx(fast)
