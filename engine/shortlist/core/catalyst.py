import calendar
from datetime import date, timedelta

from shortlist.config import Catalyst


def hints(sector: str, cfg: Catalyst) -> dict:
    if sector in cfg.hints:
        return {"sector_matched": True, "items": cfg.hints[sector]}
    return {"sector_matched": False, "items": cfg.default_hints}


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def statement_deadlines(today: date, cfg: Catalyst) -> list[dict]:
    """Estimated filing deadlines: N days after each quarter end, longer for the annual statement."""
    out = []
    for year in (today.year - 1, today.year, today.year + 1):
        for q in range(1, 5):
            quarter_end = date(year, q * 3, calendar.monthrange(year, q * 3)[1])
            if q == 4:
                due = quarter_end + timedelta(days=cfg.annual_deadline_days)
                label = f"กำหนดส่งงบปี {year}"
            else:
                due = quarter_end + timedelta(days=cfg.quarter_deadline_days)
                label = f"กำหนดส่งงบไตรมาส {q}/{year}"
            if due >= today:
                out.append({"date": due.isoformat(), "label": label, "kind": "statement", "estimated": True})
    return out


def next_statement_deadline(today: date, cfg: Catalyst) -> date:
    return date.fromisoformat(statement_deadlines(today, cfg)[0]["date"])


def event_calendar(today: date, cfg: Catalyst, manual_events: list[dict]) -> list[dict]:
    end = add_months(today, cfg.horizon_months).isoformat()
    start = today.isoformat()
    events = statement_deadlines(today, cfg)
    events += [
        {"date": r.date.isoformat(), "label": r.label, "kind": "index_review", "estimated": True}
        for r in cfg.index_reviews
    ]
    events += [
        {"id": e["id"], "date": e["date"], "label": e["text"], "kind": "manual", "estimated": False}
        for e in manual_events
    ]
    return sorted((e for e in events if start <= e["date"] <= end), key=lambda e: e["date"])
