from datetime import date

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
