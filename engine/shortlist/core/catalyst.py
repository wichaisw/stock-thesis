import calendar
from datetime import date, timedelta

import pandas as pd

from shortlist.config import Catalyst


def hints(sector: str, cfg: Catalyst) -> dict:
    if sector in cfg.hints:
        return {"sector_matched": True, "items": cfg.hints[sector]}
    return {"sector_matched": False, "items": cfg.default_hints}


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def statement_due(year: int, q: int, cfg: Catalyst) -> tuple[date, str]:
    """Estimated filing deadline of one calendar quarter: N days after its end, longer for the annual statement."""
    quarter_end = date(year, q * 3, calendar.monthrange(year, q * 3)[1])
    if q == 4:
        return quarter_end + timedelta(days=cfg.annual_deadline_days), f"กำหนดส่งงบปี {year}"
    return quarter_end + timedelta(days=cfg.quarter_deadline_days), f"กำหนดส่งงบไตรมาส {q}/{year}"


def statement_deadlines(today: date, cfg: Catalyst) -> list[dict]:
    out = []
    for year in (today.year - 1, today.year, today.year + 1):
        for q in range(1, 5):
            due, label = statement_due(year, q, cfg)
            if due >= today:
                out.append({"date": due.isoformat(), "label": label, "kind": "statement", "estimated": True})
    return out


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


def earnings_due(latest_quarter: str, price_date: date, days: int, cfg: Catalyst) -> dict:
    """The quarter after the latest reported one is due within `days` of the run's price date (add-risk-flags D4).
    Reported already, or past its deadline, is not flagged."""
    nxt = pd.Period(latest_quarter, "Q") + 1
    due, _ = statement_due(nxt.year, nxt.quarter, cfg)
    if not price_date <= due <= price_date + timedelta(days=days):
        return {"flag": False, "reason": None}
    return {
        "flag": True,
        "quarter": str(nxt),
        "date": due.isoformat(),
        "reason": f"งบ {nxt} ครบกำหนดส่งประมาณ {due:%d/%m/%Y} (ค่าประมาณจากไตรมาสปฏิทิน)",
    }
