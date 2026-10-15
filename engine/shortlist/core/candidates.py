import math

from shortlist.config import Candidates

# short names for reasons; the panel keeps the long labels with formulas
SHORT = {
    "pe_median": "PE band", "pe_minus_1sd": "PE band − 1SD", "pbv_median": "PBV band",
    "dividend_yield_median": "Dividend yield band", "peer_pe": "Peer PE", "justified_pbv": "Justified PBV",
}


def inclusion(ev: dict, cfg: Candidates) -> dict:
    """Why a stock is (not) a candidate. `ev` holds the liquidity/quality/fair_value/cdc results."""
    reasons = []
    if not ev["liquidity"]["passed"]:
        reasons.append(f"ไม่ผ่าน liquidity filter: {ev['liquidity']['reason']}")
    elif not ev["quality"]["passed"]:
        failed = [c["reason"] for c in ev["quality"]["checks"] if c["passed"] is False]
        reasons.append(f"ไม่ผ่าน quality gate: {', '.join(failed)}")

    if ev.get("fair_value") is not None:
        gate = ev["fair_value"]["gate"]
        if gate["mos"] is None:
            reasons.append("ไม่มี gate method ที่คำนวณได้ (Peer PE, Justified PBV)")
        for item in gate["items"]:
            if item["mos"] is not None and item["mos"] < cfg.min_gate_mos:
                reasons.append(f"MoS ของ {SHORT[item['method']]} {item['mos']:.1%} ต่ำกว่าเกณฑ์ {cfg.min_gate_mos:.0%}")

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
        -ev["fair_value"]["gate"]["mos"],
    )


def rank(evaluations: list[dict], cfg: Candidates) -> list[dict]:
    """Candidates in display order. Plain gate + sort: no weighted score by design."""
    return sorted((ev for ev in evaluations if inclusion(ev, cfg)["included"]), key=sort_key)
