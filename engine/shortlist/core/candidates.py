import math

from shortlist.config import Candidates, RiskReward
from shortlist.core import fair_value, risk_reward

# short names for reasons; the panel keeps the long labels with formulas
SHORT = {
    "pe_median": "PE band", "pe_minus_1sd": "PE band − 1SD", "pbv_median": "PBV band",
    "dividend_yield_median": "Dividend yield band", "peer_pe": "Peer PE", "justified_pbv": "Justified PBV",
}
# the only methods the candidates page may toggle: the others were never backtested as a gate
TOGGLEABLE = ["peer_pe", "justified_pbv"]


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
        # no gate chosen on the candidates page is not the same as chosen but not computable (candidate-gate-toggle D4)
        if gate["methods"] and gate["mos"] is None:
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
    mos = ev["fair_value"]["gate"]["mos"]
    return (
        ev["cdc"]["state"] != "just-crossed",
        eta if eta is not None else math.inf,
        # with no gate chosen there is no MoS to rank by, so the symbol keeps the order stable
        -mos if mos is not None else 0,
        ev["symbol"],
    )


def rank(evaluations: list[dict], cfg: Candidates) -> list[dict]:
    """Candidates in display order. Plain gate + sort: no weighted score by design."""
    return sorted((ev for ev in evaluations if inclusion(ev, cfg)["included"]), key=sort_key)


def regate(evaluations: list[dict], methods: list[str], cfg: Candidates, rr: RiskReward) -> list[dict]:
    """Candidates in display order under other gate methods, from a run's stored evaluations (candidate-gate-toggle D1).
    Mutates the evaluations; callers pass rows freshly read from the DB."""
    cfg = cfg.model_copy(update={"gate_methods": methods})
    for ev in evaluations:
        fv = ev.get("fair_value")
        if fv is not None:
            min_mos = (fv.get("gate") or {}).get("min_mos", cfg.min_gate_mos)
            fv["gate"] = fair_value.gate(fv["items"], methods) | {"min_mos": min_mos}
            old = ev.get("risk_reward") or {}
            # entry and stop do not depend on the gate, so the stored ones are reused (design D3)
            if old.get("entry") is not None and old.get("stop") is not None:
                ev["risk_reward"] = old | risk_reward.levels(old["entry"], old["stop"], fv, rr)
        ev["inclusion"] = inclusion(ev, cfg)
        ev["candidate_rank"] = None
    ranked = rank(evaluations, cfg)
    for n, ev in enumerate(ranked, start=1):
        ev["candidate_rank"] = n
    return ranked
