"""Phase 0 spike (design D8): does `bear-approaching` lead to a cross, and does it pay?

Uses 3 years of prices for every stock. A day only counts when the stock passed the
liquidity filter on that day (its own trailing traded value), so today's liquidity does
not leak into the past. For each `bear-approaching` day it checks whether Fast crosses
above Slow within the next `approaching_eta_days` trading days, and the close-to-close
return 20 and 60 trading days later. `bear-far` days are the baseline.

Delisted stocks are missing from yfinance, so survivorship bias remains.

    uv run python scripts/backtest_cdc.py
"""

import pandas as pd

from shortlist.config import Config, load_config
from shortlist.core import cdc
from shortlist.sources.thaifin_source import ThaifinFinancials
from shortlist.sources.yahoo import YahooPrices

RETURN_HORIZONS = (20, 60)


def daily_states(prices: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    c = cfg.cdc
    df = cdc.lines(prices, c)
    gap = (df["slow"] - df["fast"]) / df["slow"]
    speed = (gap.shift(c.speed_window) - gap) / c.speed_window
    above = df["fast"] > df["slow"]
    eta = (gap / speed).where(speed > 0)
    approaching = ~above & (eta <= c.approaching_eta_days)
    horizon = int(c.approaching_eta_days)
    # crossed[t] is True when a bull cross happens on any of the next `horizon` days
    cross_day = above & ~above.shift(1, fill_value=False)
    crossed = cross_day[::-1].rolling(horizon, min_periods=1).max()[::-1].shift(-1).astype("boolean")

    l = cfg.liquidity
    traded = (prices["close"] * prices["volume"]).rolling(l.window_days).mean()
    liquid = traded >= l.min_avg_traded_value

    out = pd.DataFrame({
        "approaching": approaching & liquid,
        "bear_far": ~above & ~approaching & liquid,
        "crossed": crossed,
        # NaN near the end of history, where the outcome is not known yet
        **{f"ret{n}": prices["close"].shift(-n) / prices["close"] - 1 for n in RETURN_HORIZONS},
    })
    # skip EMA warm-up and the tail whose cross outcome is not known yet
    return out.iloc[c.min_days : len(out) - horizon]


def episode_starts(flags: pd.Series) -> pd.Series:
    return flags & ~flags.shift(1, fill_value=False)


def main() -> None:
    cfg = load_config()
    stocks = ThaifinFinancials(cfg.batch.markets).list_stocks()
    prices = YahooPrices("3y", cfg.batch.price_chunk_size, cfg.batch.chunk_delay_seconds).fetch_prices(
        [s.symbol for s in stocks]
    )
    frames = [daily_states(p, cfg) for p in prices.values()]
    liquid_stocks = sum(bool((f["approaching"] | f["bear_far"]).any()) for f in frames)
    print(f"หุ้นที่มีราคา {len(prices)} ตัว, เคยผ่าน liquidity อย่างน้อย 1 วัน {liquid_stocks} ตัว")

    horizon = int(cfg.cdc.approaching_eta_days)
    header = f"{'state':<22}{'นับแบบ':<10}{'จำนวน':>8}{f'% cross ใน {horizon} วัน':>20}"
    header += "".join(f"{f'median {n} วัน':>14}" for n in RETURN_HORIZONS)
    print("\n" + header)
    for label, col in [("bear-approaching", "approaching"), ("bear-far (baseline)", "bear_far")]:
        for unit, pick in [("ทุกวัน", lambda f: f[col]), ("ครั้งที่เข้า", lambda f: episode_starts(f[col]))]:
            rows = pd.concat([f.loc[pick(f)] for f in frames])
            line = f"{label:<22}{unit:<10}{len(rows):>8}{rows['crossed'].mean():>20.1%}"
            line += "".join(f"{rows[f'ret{n}'].median():>14.2%}" for n in RETURN_HORIZONS)
            print(line)


if __name__ == "__main__":
    main()
