from datetime import date

import pandas as pd
import pytest

from shortlist.config import load_config
from shortlist.core import exit

CFG = load_config()
FLAT = [12.0] * 80
# bar 79 (the last flat bar) is the buy date in most tests
DAYS = pd.bdate_range("2026-01-01", periods=200)
BUY = DAYS[79].date()


def prices(closes: list[float]) -> pd.DataFrame:
    """Lows sit 0.20 under the close, so the flat stretch has a 20-day low of 11.80 and Slow 12.00."""
    close = pd.Series(closes, index=DAYS[: len(closes)])
    return pd.DataFrame({"open": close, "high": close, "low": close - 0.2, "close": close})


def ev(price: float, state: str | None = "bull", quality: bool | None = True, mos: float | None = 0.2) -> dict:
    statements = quality is not None
    return {
        "price": price,
        "price_date": "2026-06-01",
        "cdc": {"state": state, "reason": None if state else "ข้อมูลราคาไม่พอ (30/60 วันทำการ)"},
        "quality": {"passed": quality, "checks": [{"passed": quality, "reason": "D/E 2.30 เกิน 1.5"}]} if statements else None,
        "fair_value": {"gate": {"mos": mos}} if statements else None,
    }


def run(closes: list[float], cost: float = 12.0, buy: date = BUY, **kw) -> dict:
    return exit.evaluate(cost, buy, ev(closes[-1], **kw), prices(closes), CFG)


def test_stop_frozen_at_buy_date():
    # at the buy date: 20-day low 11.80, Slow 12.00 x 0.97 = 11.64; the later rise does not move it
    r = run(FLAT + [12 + 0.1 * i for i in range(1, 21)])
    assert r["stop"] == 11.64


def test_buy_on_saturday_uses_friday():
    friday = next(d for d in DAYS[70:80] if d.dayofweek == 4)
    # a dip right after the Friday shows the stop ignores bars past the buy date
    closes = FLAT[:DAYS.get_loc(friday) + 1] + [11.0] * 5
    saturday = (friday + pd.offsets.Day(1)).date()
    assert run(closes, buy=saturday)["stop"] == run(closes, buy=friday.date())["stop"] == 11.64


def test_buy_older_than_prices_has_no_stop():
    r = run(FLAT, buy=date(2025, 1, 2))
    assert r["stop"] is None
    assert any("ไม่มีราคา ณ วันที่ซื้อ" in t for t in r["tags"])


def test_close_below_stop_is_cut_even_before_first_cross():
    r = run(FLAT + [11.5, 11.2], state="bear-approaching")
    assert r["verdict"] == "cut"
    assert "ราคา 11.20 ต่ำกว่า stop 11.64" in r["reasons"]
    assert "รอ CDC cross ครั้งแรก" in r["tags"]


def test_bear_after_bull_since_buy_is_cut():
    up = [12 + 0.1 * i for i in range(1, 21)]
    down = [14 - 0.08 * i for i in range(1, 21)]
    r = run(FLAT + up + down, state="bear-far")
    assert r["verdict"] == "cut"
    assert "CDC ตัดลงเป็น bear (bear-far)" in r["reasons"]


def test_bear_before_first_cross_is_not_cut():
    r = run(FLAT + [11.9] * 5, cost=11.9, state="bear-approaching")
    assert r["verdict"] == "hold"
    assert r["reasons"] == []
    assert "รอ CDC cross ครั้งแรก" in r["tags"]


def test_quality_fail_is_cut():
    r = run(FLAT + [12.0] * 5, quality=False)
    assert r["verdict"] == "cut"
    assert "ไม่ผ่าน quality gate: D/E 2.30 เกิน 1.5" in r["reasons"]


def test_low_gate_mos_is_prepare():
    r = run(FLAT + [12.0] * 5, mos=0.06)
    assert r["verdict"] == "prepare"
    assert "MoS gate 6.0% ต่ำกว่า 10%" in r["reasons"]


def test_bull_ending_is_prepare():
    # a sharp rise then a flat stretch: Fast sinks back toward Slow
    r = run(FLAT + [12 + 0.2 * i for i in range(1, 11)] + [14.0] * 20)
    assert r["verdict"] == "prepare"
    assert any(x.startswith("CDC bull ใกล้จบ: ETA ตัดลง") for x in r["reasons"])


def test_no_gate_method_skips_upside():
    r = run(FLAT + [12.5] * 5, mos=None)
    assert r["verdict"] == "hold"
    assert "ไม่มี gate method ที่คำนวณได้" in r["tags"]


def test_no_statements_skips_quality_and_upside_but_keeps_stop():
    r = run(FLAT + [11.2], quality=None)
    assert r["verdict"] == "cut"
    assert any(t.startswith("ยังไม่มีงบ") for t in r["tags"])


def test_below_cost_with_thesis_intact_is_wait():
    r = run(FLAT + [11.9] * 5, cost=12.5)
    assert r["verdict"] == "wait"


def test_above_cost_is_hold():
    assert run(FLAT + [12.0] * 5, cost=11.0)["verdict"] == "hold"


def test_cut_shows_every_reason():
    r = run(FLAT + [11.2], mos=0.05)
    assert r["verdict"] == "cut"
    assert "ราคา 11.20 ต่ำกว่า stop 11.64" in r["reasons"]
    assert "MoS gate 5.0% ต่ำกว่า 10%" in r["reasons"]


def test_held_over_a_quarter_is_a_tag_only():
    r = run(FLAT + [12.0] * 70, cost=11.0)
    assert r["verdict"] == "hold"
    assert "ถือเกินหนึ่งไตรมาส (70 วันทำการ)" in r["tags"]


def test_pnl():
    assert run(FLAT + [10.8], cost=10.0)["pnl"] == pytest.approx(0.08)


def test_no_evaluation_is_no_data():
    r = exit.evaluate(12.0, BUY, None, prices(FLAT), CFG, failure="ไม่มีข้อมูลราคา")
    assert r["verdict"] == "no_data"
    assert r["reasons"] == ["ไม่มีข้อมูลราคา"]


def test_close_equal_to_the_shown_stop_is_not_below():
    # a stop of 11.6400001 shows as 11.64; a close of 11.64 is not under it
    r = run(FLAT + [11.64], cost=11.0)
    assert r["stop"] == 11.64 and r["verdict"] == "hold"
