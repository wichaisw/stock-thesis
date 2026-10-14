import pandas as pd

from shortlist.config import Cdc
from shortlist.core import num


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def lines(prices: pd.DataFrame, cfg: Cdc) -> pd.DataFrame:
    if cfg.source == "ohlc4":
        src = (prices["open"] + prices["high"] + prices["low"] + prices["close"]) / 4
    else:
        src = prices["close"]
    ap = ema(src, cfg.ap_length)
    return pd.DataFrame({"ap": ap, "fast": ema(ap, cfg.fast_length), "slow": ema(ap, cfg.slow_length)})


def evaluate(prices: pd.DataFrame, cfg: Cdc) -> dict:
    if len(prices) < cfg.min_days:
        return {"state": None, "reason": f"ข้อมูลราคาไม่พอ ({len(prices)}/{cfg.min_days} วันทำการ)"}
    df = lines(prices, cfg)
    return classify(df["fast"], df["slow"], cfg)


def classify(fast: pd.Series, slow: pd.Series, cfg: Cdc) -> dict:
    gap = (slow - fast) / slow
    n = cfg.speed_window
    speed = (gap.iloc[-1 - n] - gap.iloc[-1]) / n
    above = (fast > slow).to_numpy()

    days_since_cross = None
    eta = None
    if above[-1]:
        below_idx = (~above).nonzero()[0]
        if len(below_idx):
            days_since_cross = int(len(above) - 1 - below_idx[-1] - 1)
        # a cross older than the price history is just a long-running bull
        crossed_recently = days_since_cross is not None and days_since_cross < cfg.just_crossed_days
        state = "just-crossed" if crossed_recently else "bull"
    else:
        eta = gap.iloc[-1] / speed if speed > 0 else None
        state = "bear-approaching" if eta is not None and eta <= cfg.approaching_eta_days else "bear-far"

    return {
        "state": state,
        "fast": num(fast.iloc[-1]),
        "slow": num(slow.iloc[-1]),
        "gap_pct": num(gap.iloc[-1]),
        "speed": num(speed),
        "eta_days": num(eta, 1),
        "days_since_cross": days_since_cross,
        "reason": None,
    }
