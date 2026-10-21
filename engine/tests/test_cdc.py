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


PRICES = pd.DataFrame(
    {"open": [10.0, 11.0, 12.0], "high": [12.0, 13.0, 14.0], "low": [8.0, 9.0, 10.0], "close": [10.5, 11.5, 12.5]}
)


def ema_list(xs: list[float], length: int) -> list[float]:
    out = [xs[0]]
    for x in xs[1:]:
        out.append(out[-1] + (2 / (length + 1)) * (x - out[-1]))
    return out


def test_default_matches_tradingview_v3_settings():
    # CDC ActionZone V3 2020 "close 12 26 1": no smoothing, so AP is the close itself
    df = cdc.lines(PRICES, CFG)
    close = PRICES["close"].tolist()
    assert df["ap"].tolist() == pytest.approx(close)
    assert df["fast"].tolist() == pytest.approx(ema_list(close, 12))
    assert df["slow"].tolist() == pytest.approx(ema_list(close, 26))


def test_lines_follow_ohlc4_formula():
    df = cdc.lines(PRICES, CFG.model_copy(update={"source": "ohlc4", "ap_length": 2}))
    ap = ema_list([10.125, 11.125, 12.125], 2)
    assert df["ap"].tolist() == pytest.approx(ap)
    assert df["fast"].tolist() == pytest.approx(ema_list(ap, 12))


def test_bull_gap_narrowing_gives_eta():
    # bull gap 2% five days ago, 1% today -> speed 0.2%/day -> ETA 5
    fast, slow = lines_with_gap([-0.03] * 60 + [-0.02, -0.018, -0.016, -0.014, -0.012, -0.01])
    assert cdc.bull_eta(fast, slow, CFG) == pytest.approx(5)


def test_bull_gap_widening_has_no_eta():
    fast, slow = lines_with_gap([-0.01] * 60 + [-0.01, -0.012, -0.014, -0.016, -0.018, -0.02])
    assert cdc.bull_eta(fast, slow, CFG) is None


def test_bull_eta_none_when_bear():
    fast, slow = lines_with_gap([0.03] * 60 + [0.02, 0.018, 0.016, 0.014, 0.012, 0.01])
    assert cdc.bull_eta(fast, slow, CFG) is None


def test_bull_state_still_has_no_eta_in_classify():
    fast, slow = lines_with_gap([-0.03] * 60 + [-0.02, -0.018, -0.016, -0.014, -0.012, -0.01])
    r = cdc.classify(fast, slow, CFG)
    assert r["state"] == "bull"
    assert r["eta_days"] is None
