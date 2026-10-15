import pandas as pd

from shortlist.config import load_config
from shortlist.core import fair_value, risk_reward

CFG = load_config().risk_reward


def prices(close: float = 12.40, low: float = 11.80) -> pd.DataFrame:
    return pd.DataFrame({"close": [close] * 20, "low": [low] * 20})


def fv(target: float | None, top: float | None = None, median: float | None = None) -> dict:
    """Peer PE's fair value is `target`; Justified PBV is not computable."""
    items = [{"method": "peer_pe", "fair_value": target, "mos": 0.1 if target else None, "reason": None},
             {"method": "justified_pbv", "fair_value": None, "mos": None, "reason": "คำนวณไม่ได้"}]
    return {"summary": {"median_fair_value": median or target, "max_fair_value": top or target},
            "gate": fair_value.gate(items, ["peer_pe", "justified_pbv"])}


def test_stop_takes_the_lower_of_swing_low_and_slow_buffer():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value=fv(14.2), cfg=CFG)
    assert r["stop"] == 11.50


def test_rrr_at_threshold_has_no_warning():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value=fv(14.2, 16.0), cfg=CFG)
    assert r["rrr"] == 2.0
    assert not r["low_rrr"]
    assert r["target_optimistic"] == 16.0


def test_low_rrr_is_flagged():
    # (13.48 - 12.40) / (12.40 - 11.50) = 1.2
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value=fv(13.48), cfg=CFG)
    assert r["rrr"] == 1.2
    assert r["low_rrr"]


def test_no_upside_is_na():
    r = risk_reward.evaluate(prices(), slow=12.0, fair_value=fv(12.0), cfg=CFG)
    assert r["rrr"] is None
    assert "ไม่มี upside" in r["reason"]


def test_no_fair_value_is_na():
    r = risk_reward.evaluate(prices(), slow=12.0, fair_value=fv(None), cfg=CFG)
    assert r["rrr"] is None and r["reason"]


def test_stop_above_entry_is_na():
    r = risk_reward.evaluate(prices(close=12.40, low=12.50), slow=None, fair_value=fv(14.0), cfg=CFG)
    assert r["rrr"] is None and "stop" in r["reason"]


def test_upside_above_threshold_is_flagged():
    r = risk_reward.evaluate(prices(close=2.70, low=2.50), slow=None, fair_value=fv(15.73), cfg=CFG)
    assert r["upside"] > 4.8
    assert r["high_upside"]


def test_upside_below_threshold_has_no_warning():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value=fv(14.2), cfg=CFG)
    assert r["upside"] == 0.1452
    assert not r["high_upside"]


def test_no_upside_has_no_high_upside_warning():
    for target in (12.0, None):
        r = risk_reward.evaluate(prices(), slow=12.0, fair_value=fv(target), cfg=CFG)
        assert not r["high_upside"]


def test_target_is_the_lower_gate_method_not_the_median():
    items = [{"method": "peer_pe", "fair_value": 15.0, "mos": 0.17, "reason": None},
             {"method": "justified_pbv", "fair_value": 14.2, "mos": 0.127, "reason": None}]
    f = {"summary": {"median_fair_value": 18.0, "max_fair_value": 20.0},
         "gate": fair_value.gate(items, ["peer_pe", "justified_pbv"])}
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value=f, cfg=CFG)
    assert (r["target"], r["target_optimistic"]) == (14.2, 20.0)


def test_no_gate_method_is_na_even_when_the_panel_has_values():
    r = risk_reward.evaluate(prices(), slow=12.0, fair_value=fv(None, top=20.0, median=18.0), cfg=CFG)
    assert r["target"] is None and r["rrr"] is None
    assert r["reason"] == "ไม่มี gate method ที่คำนวณได้"
