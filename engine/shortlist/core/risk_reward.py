import pandas as pd

from shortlist.config import RiskReward
from shortlist.core import num


def stop_level(prices: pd.DataFrame, slow: float | None, cfg: RiskReward) -> float:
    swing_low = float(prices["low"].tail(cfg.swing_low_days).min())
    # without enough history for CDC there is no Slow EMA, so the swing low alone sets the stop
    return min(swing_low, slow * (1 - cfg.stop_buffer)) if slow else swing_low


def evaluate(prices: pd.DataFrame, slow: float | None, fair_value: dict, cfg: RiskReward) -> dict:
    return levels(float(prices["close"].iloc[-1]), stop_level(prices, slow, cfg), fair_value, cfg)


def levels(entry: float, stop: float, fair_value: dict, cfg: RiskReward) -> dict:
    """Target is the lower fair value of the gate methods, never the panel median (design D6: no fallback),
    unless no gate method is chosen at all (candidate-gate-toggle D4)."""
    no_gate = not fair_value["gate"]["methods"]
    target = fair_value["summary"]["median_fair_value"] if no_gate else fair_value["gate"]["fair_value"]

    result = {
        "entry": num(entry, 2),
        "stop": num(stop, 2),
        "target": target,
        "target_source": "median" if no_gate else "gate",
        "target_optimistic": fair_value["summary"]["max_fair_value"],
        "rrr": None,
        "low_rrr": False,
        "upside": None,
        "high_upside": False,
        "reason": None,
    }
    if target is None:
        return result | {"reason": "ไม่มีเกณฑ์ที่คำนวณได้" if no_gate else "ไม่มี gate method ที่คำนวณได้"}
    if target <= entry:
        return result | {"reason": "ไม่มี upside (ราคาสูงกว่า target แล้ว)"}
    upside = (target - entry) / entry
    result |= {"upside": num(upside, 4), "high_upside": upside > cfg.max_upside}
    if stop >= entry:
        return result | {"reason": "stop ไม่ต่ำกว่า entry"}
    # rounded first so 1.9999 from float noise is not flagged as below 2
    rrr = round((target - entry) / (entry - stop), 2)
    return result | {"rrr": rrr, "low_rrr": rrr < cfg.min_rrr}
