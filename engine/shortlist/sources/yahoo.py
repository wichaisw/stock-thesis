import time
import urllib.error
import urllib.request
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


REACHABILITY_URL = "https://query2.finance.yahoo.com"


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
        return quarterly_market_cap(_naive(px["Close"]), _naive(px["Stock Splits"]), shares, _naive(px["Dividends"]))

    def reachable(self) -> str | None:
        # yfinance reports a network outage as "possibly delisted; no price data found", so ask the host directly
        try:
            with urllib.request.urlopen(REACHABILITY_URL, timeout=5):
                return None
        except urllib.error.HTTPError:
            return None  # any HTTP reply, even 429, means the network reaches Yahoo
        except OSError as e:
            return f"เชื่อมต่อแหล่งราคาไม่ได้: {e}"


# Net Income, not Net Income Common Stockholders: the latter subtracts perpetual-debenture interest and so
# misses SET and thaifin (README, prefer-yfinance-statements task 1.1)
STATEMENT_ROWS = {"net_profit": "Net Income", "equity": "Stockholders Equity"}
STATEMENT_COLUMNS = list(STATEMENT_ROWS)


def to_statements(income: pd.DataFrame, balance: pd.DataFrame, currency: str | None) -> pd.DataFrame:
    """Parent-company net profit and equity per quarter label; empty unless the statements are in baht (design D4)."""
    if currency != "THB":
        return pd.DataFrame(columns=STATEMENT_COLUMNS)
    rows = {}
    for col, row in STATEMENT_ROWS.items():
        stmt = income if col == "net_profit" else balance
        rows[col] = stmt.loc[row] if row in stmt.index else pd.Series(dtype=float)
    df = pd.DataFrame(rows, columns=STATEMENT_COLUMNS).apply(pd.to_numeric, errors="coerce").dropna(how="all")
    df.index = [str(pd.Timestamp(d).to_period("Q")) for d in df.index]
    df.index.name = "quarter"
    return df.sort_index()


def fetch_statements(symbol: str) -> pd.DataFrame:
    """Never raises: statements are a supplement, so thaifin covers any failure (design D5)."""
    try:
        t = yf.Ticker(f"{symbol}.BK")
        return to_statements(t.quarterly_income_stmt, t.quarterly_balance_sheet, t.info.get("financialCurrency"))
    except Exception:
        return pd.DataFrame(columns=STATEMENT_COLUMNS)


def _naive(s: pd.Series) -> pd.Series:
    s = s.copy()
    s.index = pd.DatetimeIndex(s.index).tz_localize(None).normalize()
    return s


def quarterly_market_cap(
    close: pd.Series, splits: pd.Series, shares: pd.Series, dividends: pd.Series | None = None
) -> pd.DataFrame:
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
    # Dividends and Close are both split-adjusted, so their ratio is the yield at the traded price and
    # the trailing sum is already per share of today's count; stock dividends sit in splits, not here
    divs = dividends[dividends > 0] if dividends is not None and len(dividends) else None
    adjusted = close.dropna()
    last_day = adjusted.groupby(adjusted.index.to_period("Q")).apply(lambda s: s.index[-1])
    dps = pd.Series(
        [0.0 if divs is None else divs[(divs.index > d - pd.Timedelta(days=365)) & (divs.index <= d)].sum() for d in last_day],
        index=last_day.index,
    )
    out = pd.DataFrame(
        {
            "mkt_cap": q_close * q_shares,
            "shares": q_shares,
            "dps_ttm": dps,
            "dividend_yield_ttm": dps / adjusted.groupby(adjusted.index.to_period("Q")).last(),
        }
    )
    out.index = [str(q) for q in out.index]
    out.index.name = "quarter"
    return out
