from datetime import date, timedelta

import pandas as pd
import pytest

from shortlist.config import load_config
from shortlist.core import risk_reward

CFG = load_config().risk_reward
TODAY = date(2026, 10, 14)
NEXT = TODAY + timedelta(days=60)


def prices(close: float = 12.40, low: float = 11.80) -> pd.DataFrame:
    return pd.DataFrame({"close": [close] * 20, "low": [low] * 20})


def summary(median: float | None, top: float | None = None) -> dict:
    return {"median_fair_value": median, "max_fair_value": top or median}


def test_stop_takes_the_lower_of_swing_low_and_slow_buffer():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value_summary=summary(14.2), today=TODAY,
                             next_deadline=NEXT, cfg=CFG)
    assert r["stop"] == 11.50


def test_rrr_at_threshold_has_no_warning():
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value_summary=summary(14.2, 16.0), today=TODAY,
                             next_deadline=NEXT, cfg=CFG)
    assert r["rrr"] == 2.0
    assert not r["low_rrr"]
    assert r["target_optimistic"] == 16.0


def test_low_rrr_is_flagged():
    # (13.48 - 12.40) / (12.40 - 11.50) = 1.2
    r = risk_reward.evaluate(prices(), slow=11.50 / 0.97, fair_value_summary=summary(13.48), today=TODAY,
                             next_deadline=NEXT, cfg=CFG)
    assert r["rrr"] == 1.2
    assert r["low_rrr"]


def test_no_upside_is_na():
    r = risk_reward.evaluate(prices(), slow=12.0, fair_value_summary=summary(12.0), today=TODAY,
                             next_deadline=NEXT, cfg=CFG)
    assert r["rrr"] is None
    assert "ไม่มี upside" in r["reason"]


def test_no_fair_value_is_na():
    r = risk_reward.evaluate(prices(), slow=12.0, fair_value_summary=summary(None), today=TODAY,
                             next_deadline=NEXT, cfg=CFG)
    assert r["rrr"] is None and r["reason"]


def test_stop_above_entry_is_na():
    r = risk_reward.evaluate(prices(close=12.40, low=12.50), slow=None, fair_value_summary=summary(14.0),
                             today=TODAY, next_deadline=NEXT, cfg=CFG)
    assert r["rrr"] is None and "stop" in r["reason"]


def months_ahead(m: float) -> date:
    return TODAY + timedelta(days=round(m * risk_reward.DAYS_PER_MONTH))


def test_reward_per_month_with_statement_soon_uses_one_month_floor():
    # upside 15%: entry 10, target 11.5
    r = risk_reward.evaluate(prices(close=10.0, low=9.0), slow=None, fair_value_summary=summary(11.5),
                             today=TODAY, next_deadline=months_ahead(0.5), cfg=CFG)
    assert r["hold_months"] == 1
    assert r["reward_per_month"] == pytest.approx(0.15)


def test_reward_per_month_with_statement_far():
    r = risk_reward.evaluate(prices(close=10.0, low=9.0), slow=None, fair_value_summary=summary(11.5),
                             today=TODAY, next_deadline=months_ahead(2.5), cfg=CFG)
    assert r["reward_per_month"] == pytest.approx(0.06, abs=0.001)
