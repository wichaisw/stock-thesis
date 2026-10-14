"""Phase 0 spike (design D8): how often does `bear-approaching` become a real cross?

Uses 3 years of prices for stocks that pass today's liquidity filter. For every day a
stock is `bear-approaching`, checks whether Fast crosses above Slow within the next
`approaching_eta_days` trading days. `bear-far` days are the baseline.

    uv run python scripts/backtest_cdc.py
"""

import pandas as pd

from shortlist.config import load_config
from shortlist.core import cdc
from shortlist.core.quality import liquidity
from shortlist.sources.thaifin_source import ThaifinFinancials
from shortlist.sources.yahoo import YahooPrices


def daily_states(prices: pd.DataFrame, cfg) -> pd.DataFrame:
    df = cdc.lines(prices, cfg)
    gap = (df["slow"] - df["fast"]) / df["slow"]
    speed = (gap.shift(cfg.speed_window) - gap) / cfg.speed_window
    above = df["fast"] > df["slow"]
    eta = (gap / speed).where(speed > 0)
    approaching = ~above & (eta <= cfg.approaching_eta_days)
    horizon = int(cfg.approaching_eta_days)
    # crossed[t] is True when a bull cross happens on any of the next `horizon` days
    cross_day = above & ~above.shift(1, fill_value=False)
    crossed = cross_day[::-1].rolling(horizon, min_periods=1).max()[::-1].shift(-1).astype("boolean")
    out = pd.DataFrame({"approaching": approaching, "bear_far": ~above & ~approaching, "crossed": crossed})
    # skip EMA warm-up and the tail whose outcome is not known yet
    return out.iloc[cfg.min_days : len(out) - horizon]


def episode_starts(flags: pd.Series) -> pd.Series:
    return flags & ~flags.shift(1, fill_value=False)


def main() -> None:
    cfg = load_config()
    stocks = ThaifinFinancials(cfg.batch.markets).list_stocks()
    prices = YahooPrices("3y", cfg.batch.price_chunk_size, cfg.batch.chunk_delay_seconds).fetch_prices(
        [s.symbol for s in stocks]
    )
    liquid = {s: p for s, p in prices.items() if liquidity(p, cfg.liquidity)["passed"]}
    print(f"หุ้นที่มีราคา {len(prices)} ตัว, ผ่าน liquidity {len(liquid)} ตัว")

    frames = [daily_states(p, cfg.cdc) for p in liquid.values()]
    rows = []
    for label, col in [("bear-approaching", "approaching"), ("bear-far (baseline)", "bear_far")]:
        days = pd.concat([f.loc[f[col], "crossed"] for f in frames])
        starts = pd.concat([f.loc[episode_starts(f[col]), "crossed"] for f in frames])
        rows.append((label, len(days), days.mean(), len(starts), starts.mean()))

    horizon = int(cfg.cdc.approaching_eta_days)
    print(f"\n% ที่เกิด cross จริงภายใน {horizon} วันทำการ")
    print(f"{'state':<22}{'วัน':>8}{'% วัน':>9}{'ครั้งที่เข้า':>12}{'% ครั้ง':>9}")
    for label, n_days, p_days, n_starts, p_starts in rows:
        print(f"{label:<22}{n_days:>8}{p_days:>9.1%}{n_starts:>12}{p_starts:>9.1%}")


if __name__ == "__main__":
    main()
