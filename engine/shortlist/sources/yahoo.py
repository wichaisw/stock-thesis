import time
from itertools import batched

import pandas as pd
import yfinance as yf

from shortlist.sources import PRICE_COLUMNS


def clean_prices(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=str.lower)[PRICE_COLUMNS]
    # yfinance often returns today's row with open/high/low but no close yet
    df = df.dropna(subset=["close"])
    df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    df.columns.name = None
    return df


class YahooPrices:
    def __init__(self, period: str = "1y", chunk_size: int = 100, delay_seconds: float = 1.0):
        self.period = period
        self.chunk_size = chunk_size
        self.delay_seconds = delay_seconds

    def fetch_prices(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for i, chunk in enumerate(batched(symbols, self.chunk_size)):
            if i:
                time.sleep(self.delay_seconds)
            tickers = [f"{s}.BK" for s in chunk]
            # auto_adjust=False keeps split-adjusted, non-dividend-adjusted prices like TradingView
            raw = yf.download(
                tickers,
                period=self.period,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
            if raw is None or raw.empty:
                continue
            present = set(raw.columns.get_level_values(0))
            for symbol, ticker in zip(chunk, tickers):
                if ticker not in present:
                    continue
                df = clean_prices(raw[ticker])
                if not df.empty:
                    out[symbol] = df
        return out
