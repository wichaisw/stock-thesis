from datetime import date

import pytest

from shortlist.config import load_config
from shortlist.core import catalyst

CFG = load_config().catalyst
TODAY = date(2026, 10, 14)


def test_hotel_sector_hints():
    h = catalyst.hints("Tourism & Leisure", CFG)
    assert h["sector_matched"]
    assert any("booking" in i for i in h["items"])
    assert any("นักท่องเที่ยว" in i for i in h["items"])


def test_unknown_sector_gets_default_hints():
    h = catalyst.hints("Something New", CFG)
    assert not h["sector_matched"]
    assert h["items"] == CFG.default_hints


def test_statement_deadlines_on_14_oct_2026():
    events = catalyst.event_calendar(TODAY, CFG, [])
    statements = [(e["date"], e["label"], e["estimated"]) for e in events if e["kind"] == "statement"]
    assert statements == [
        ("2026-11-14", "กำหนดส่งงบไตรมาส 3/2026", True),
        ("2027-03-01", "กำหนดส่งงบปี 2026", True),
    ]


def test_index_reviews_within_six_months_are_estimated():
    events = catalyst.event_calendar(TODAY, CFG, [])
    reviews = [e for e in events if e["kind"] == "index_review"]
    assert [e["date"] for e in reviews] == ["2026-12-15", "2027-01-04"]
    assert all(e["estimated"] for e in reviews)


def test_manual_events_inside_horizon_only():
    manual = [
        {"id": 1, "date": "2026-12-14", "text": "XD 0.50 บาท"},
        {"id": 2, "date": "2026-10-01", "text": "ผ่านไปแล้ว"},
        {"id": 3, "date": "2027-06-01", "text": "ไกลเกิน 6 เดือน"},
    ]
    labels = [e["label"] for e in catalyst.event_calendar(TODAY, CFG, manual) if e["kind"] == "manual"]
    assert labels == ["XD 0.50 บาท"]


def test_add_months_clamps_day():
    assert catalyst.add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)


# add-risk-flags: earnings due soon


@pytest.mark.parametrize("latest,price_date,flag", [
    ("2026Q2", date(2026, 11, 5), True),    # 2026Q3 due ~14 Nov
    ("2026Q3", date(2026, 11, 5), False),   # filed early
    ("2026Q2", date(2026, 10, 15), False),  # 30 days away
    ("2026Q2", date(2026, 11, 20), False),  # deadline passed
])
def test_earnings_due(latest, price_date, flag):
    r = catalyst.earnings_due(latest, price_date, 14, CFG)
    assert r["flag"] is flag
    if flag:
        assert (r["quarter"], r["date"]) == ("2026Q3", "2026-11-14")
        assert "2026Q3" in r["reason"] and "14/11/2026" in r["reason"] and "ประมาณ" in r["reason"]


def test_annual_statement_uses_the_longer_deadline():
    r = catalyst.earnings_due("2026Q3", date(2027, 2, 20), 14, CFG)
    assert (r["flag"], r["date"]) == (True, "2027-03-01")
