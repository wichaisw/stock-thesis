from datetime import date

import pandas as pd

from shortlist.config import Config
from shortlist.core import cdc, num
from shortlist.core.risk_reward import stop_level

# order on the holdings page; a stock gets the first verdict whose rule fires
VERDICTS = ["cut", "prepare", "wait", "hold", "no_data"]
BEAR = {"bear-approaching", "bear-far"}
BULL = {"bull", "just-crossed"}
QUARTER_DAYS = 63


def evaluate(cost: float, buy_date: date, ev: dict | None, prices: pd.DataFrame, cfg: Config,
             failure: str | None = None) -> dict:
    """Exit verdict of one holding from the latest run (exit-watchlist D1). Untested heuristic, not backtested."""
    if ev is None:
        return {"verdict": "no_data", "price": None, "price_date": None, "pnl": None, "stop": None,
                "reasons": [failure or "ไม่มีผลประเมินใน run ล่าสุด"], "tags": []}

    price = ev["price"]
    reasons: dict[str, list[str]] = {v: [] for v in VERDICTS}
    tags: list[str] = []
    buy = pd.Timestamp(buy_date)
    lines = cdc.lines(prices, cfg.cdc)

    # frozen at the buy date: later bars never move it, and the adjusted history keeps it right after a split (D3)
    before = prices[prices.index <= buy]
    stop = None
    if before.empty:
        tags.append(f"ไม่มีราคา ณ วันที่ซื้อ (ราคาเริ่ม {prices.index[0]:%Y-%m-%d}) จึงไม่มี stop")
    elif len(before) < cfg.cdc.min_days:
        tags.append(f"ราคาก่อนวันที่ซื้อมีไม่พอคำนวณ stop ({len(before)}/{cfg.cdc.min_days} วันทำการ)")
    else:
        # rounded first, so a close equal to the stop as shown is not called "below" it
        stop = round(stop_level(before, float(lines["slow"].loc[before.index[-1]]), cfg.risk_reward), 2)
        if price < stop:
            reasons["cut"].append(f"ราคา {price:.2f} ต่ำกว่า stop {stop:.2f}")

    state = ev["cdc"]["state"]
    after = lines[lines.index >= buy]
    bull_since_buy = bool((after["fast"] > after["slow"]).any())
    if state is None:
        tags.append(ev["cdc"]["reason"])
    elif state in BEAR and bull_since_buy:
        reasons["cut"].append(f"CDC ตัดลงเป็น bear ({state})")
    elif state in BEAR:
        # bought before the cross (bear-approaching candidate): a bear state is the plan, not a broken trend
        tags.append("รอ CDC cross ครั้งแรก")
    elif (eta := cdc.bull_eta(lines["fast"], lines["slow"], cfg.cdc)) is not None and eta <= cfg.cdc.approaching_eta_days:
        reasons["prepare"].append(f"CDC bull ใกล้จบ: ETA ตัดลง {eta:g} วันทำการ")

    quality = ev.get("quality")
    fv = ev.get("fair_value")
    if quality is None or fv is None:
        tags.append("ยังไม่มีงบ (ไม่ใช้ quality gate และ upside)")
    else:
        if not quality["passed"]:
            failed = [c["reason"] for c in quality["checks"] if c["passed"] is False]
            reasons["cut"].append(f"ไม่ผ่าน quality gate: {', '.join(failed)}")
        mos = fv["gate"]["mos"]
        if mos is None:
            tags.append("ไม่มี gate method ที่คำนวณได้")
        elif mos < cfg.candidates.min_gate_mos:
            reasons["prepare"].append(f"MoS gate {mos:.1%} ต่ำกว่า {cfg.candidates.min_gate_mos:.0%}")

    if price < cost:
        reasons["wait"].append(f"ราคา {price:.2f} ต่ำกว่าต้นทุน {cost:.2f}")
    held = int((prices.index > buy).sum())
    if held > QUARTER_DAYS:
        tags.append(f"ถือเกินหนึ่งไตรมาส ({held} วันทำการ)")

    verdict = next((v for v in ["cut", "prepare", "wait"] if reasons[v]), "hold")
    return {
        "verdict": verdict,
        "price": price,
        "price_date": ev["price_date"],
        "pnl": num((price - cost) / cost, 4),
        "stop": num(stop, 2),
        "reasons": reasons["cut"] + reasons["prepare"] + reasons["wait"],
        "tags": tags,
    }
