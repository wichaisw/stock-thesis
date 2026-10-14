import pandas as pd

from shortlist.config import load_config
from shortlist.core import risk_reward

CFG = load_config().risk_reward


def prices(close: float = 12.40, low: float = 11.80) -> pd.DataFrame:
    return pd.DataFrame({"close": [close] * 20, "low": [low] * 20})


def summary(median: float | None, top: float | None = None) -> dict:
    return {"median_fair_value": median, "max_fair_value": top or median}


def test_stop_takes_the_lower_of_swing_low_and_slow_buffer():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value_summary=summary(14.2), cfg=CFG)
    assert r["stop"] == 11.50


def test_rrr_at_threshold_has_no_warning():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value_summary=summary(14.2, 16.0), cfg=CFG)
    assert r["rrr"] == 2.0
    assert not r["low_rrr"]
    assert r["target_optimistic"] == 16.0


def test_low_rrr_is_flagged():
    # (13.48 - 12.40) / (12.40 - 11.50) = 1.2
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value_summary=summary(13.48), cfg=CFG)
    assert r["rrr"] == 1.2
    assert r["low_rrr"]


def test_no_upside_is_na():
    r = risk_reward.evaluate(prices(), slow=12.0, fair_value_summary=summary(12.0), cfg=CFG)
    assert r["rrr"] is None
    assert "ไม่มี upside" in r["reason"]


def test_no_fair_value_is_na():
    r = risk_reward.evaluate(prices(), slow=12.0, fair_value_summary=summary(None), cfg=CFG)
    assert r["rrr"] is None and r["reason"]


def test_stop_above_entry_is_na():
    r = risk_reward.evaluate(prices(close=12.40, low=12.50), slow=None, fair_value_summary=summary(14.0), cfg=CFG)
    assert r["rrr"] is None and "stop" in r["reason"]


def test_upside_above_threshold_is_flagged():
    r = risk_reward.evaluate(prices(close=2.70, low=2.50), slow=None, fair_value_summary=summary(15.73), cfg=CFG)
    assert r["upside"] > 4.8
    assert r["high_upside"]


def test_upside_below_threshold_has_no_warning():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value_summary=summary(14.2), cfg=CFG)
    assert r["upside"] == 0.1452
    assert not r["high_upside"]


def test_no_upside_has_no_high_upside_warning():
    for target in (12.0, None):
        r = risk_reward.evaluate(prices(), slow=12.0, fair_value_summary=summary(target), cfg=CFG)
        assert not r["high_upside"]
