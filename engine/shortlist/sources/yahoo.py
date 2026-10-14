import time
from itertools import batched

import pandas as pd
import yfinance as yf

from shortlist.sources import MARKET_CAP_COLUMNS, PRICE_COLUMNS


def clean_prices(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.rename(columns=str.lower)[PRICE_COLUMNS]
    # yfinance often returns today's row with open/high/low but no close yet
    df = df.dropna(subset=["close"])
    df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
    df.index.name = "date"
    df.columns.name = None
    return df


class YahooPrices:
    def __init__(
        self, period: str = "1y", chunk_size: int = 100, delay_seconds: float = 1.0, history_period: str = "6y"
    ):
        self.period = period
        # 5-year bands need 20 quarters plus 3 more for the first TTM
        self.history_period = history_period
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

    def fetch_market_caps(self, symbol: str) -> pd.DataFrame:
        ticker = yf.Ticker(f"{symbol}.BK")
        px = ticker.history(period=self.history_period, auto_adjust=False, actions=True)
        if px.empty:
            return pd.DataFrame(columns=MARKET_CAP_COLUMNS)
        start = px.index[0]
        shares = ticker.get_shares_full(start=start.strftime("%Y-%m-%d"))
        # funds and some renamed stocks have no share count at all
        shares = _naive(shares) if shares is not None else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        return quarterly_market_cap(_naive(px["Close"]), _naive(px["Stock Splits"]), shares)


def _naive(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
    return s


def quarterly_market_cap(close: pd.Series, splits: pd.Series, shares: pd.Series) -> pd.DataFrame:
    """Market cap at each quarter end = traded close × that quarter's share count.

    yfinance's Close is already split-adjusted (stock dividends count as splits), so undo every
    split after each day to get the price that actually traded alongside that day's share count.
    """
    factor = pd.Series(1.0, index=close.index)
    for day, ratio in splits[splits > 0].items():
        factor[close.index < day] *= ratio
    traded = (close * factor).dropna()
    q_close = traded.groupby(traded.index.to_period("Q")).last()
    shares = shares[~shares.index.duplicated(keep="last")].dropna()
    # carry each count onto the trading days it was in force (never back-filled before the first one),
    # then take the median of the quarter's last 20 days: it matches the share count to the quarter-end
    # close after a mid-quarter split, and still absorbs yfinance's one-day spikes
    daily = shares.reindex(shares.index.union(traded.index)).ffill().reindex(traded.index)
    q_shares = daily.groupby(daily.index.to_period("Q")).apply(lambda s: s.tail(20).median())
    q_shares = q_shares.reindex(q_close.index)
    out = pd.DataFrame({"mkt_cap": q_close * q_shares, "shares": q_shares})
    out.index = [str(q) for q in out.index]
    out.index.name = "quarter"
    return out
