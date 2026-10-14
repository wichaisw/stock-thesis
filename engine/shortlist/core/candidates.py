import math

from shortlist.config import Candidates


def inclusion(ev: dict, cfg: Candidates) -> dict:
    """Why a stock is (not) a candidate. `ev` holds the liquidity/quality/fair_value/cdc results."""
    reasons = []
    if not ev["liquidity"]["passed"]:
        reasons.append(f"ไม่ผ่าน liquidity filter: {ev['liquidity']['reason']}")
    elif not ev["quality"]["passed"]:
        failed = [c["reason"] for c in ev["quality"]["checks"] if c["passed"] is False]
        reasons.append(f"ไม่ผ่าน quality gate: {', '.join(failed)}")

    mos = ev["fair_value"]["summary"]["median_mos"] if ev.get("fair_value") else None
    if ev.get("fair_value") is not None:
        if mos is None:
            reasons.append("fair value panel ไม่มีเกณฑ์ที่คำนวณได้")
        elif mos < cfg.min_median_mos:
            reasons.append(f"median margin of safety {mos:.1%} ต่ำกว่าเกณฑ์ {cfg.min_median_mos:.0%}")

    state = ev["cdc"]["state"]
    if state is None:
        reasons.append(ev["cdc"]["reason"])
    elif state not in cfg.accepted_states:
        reasons.append(f"CDC state {state} ไม่อยู่ในรายการที่รับ")
    return {"included": not reasons, "reasons": reasons}


def sort_key(ev: dict) -> tuple:
    eta = ev["cdc"]["eta_days"]
    return (
        ev["cdc"]["state"] != "just-crossed",
        eta if eta is not None else math.inf,
        -ev["fair_value"]["summary"]["median_mos"],
    )


def rank(evaluations: list[dict], cfg: Candidates) -> list[dict]:
    """Candidates in display order. Plain gate + sort: no weighted score by design."""
    return sorted((ev for ev in evaluations if inclusion(ev, cfg)["included"]), key=sort_key)
