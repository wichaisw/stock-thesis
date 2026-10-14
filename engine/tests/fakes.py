import numpy as np
import pandas as pd

from shortlist.sources import QUARTERLY_COLUMNS, StockInfo


def price_history(days: int = 120, start: float = 10.0, end: float = 12.0) -> pd.DataFrame:
    close = np.linspace(start, end, days)
    return pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": [5_000_000.0] * days},
        index=pd.bdate_range(end="2026-10-14", periods=days),
    )


def healthy_quarters(n: int = 16) -> pd.DataFrame:
    values = {"eps": 1.0, "net_profit": 1e9, "net_profit_yoy": 0.05, "equity": 1e9 * 4 / 0.14, "de": 0.8, "ocf": 5e8,
              "npm": 0.10, "bvps": 10.0, "dividend_yield": 0.04, "close": 15.0}
    return pd.DataFrame({c: [values[c]] * n for c in QUARTERLY_COLUMNS}, index=[f"q{i}" for i in range(n)])


class FakePrices:
    def __init__(self, prices: dict[str, pd.DataFrame]):
        self.prices = prices

    def fetch_prices(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        return {s: self.prices[s] for s in symbols if s in self.prices}


class FakeFinancials:
    def __init__(self, stocks: list[StockInfo], quarterly: dict[str, pd.DataFrame], broken: set[str] = frozenset()):
        self.stocks = stocks
        self.quarterly = quarterly
        self.broken = broken

    def list_stocks(self) -> list[StockInfo]:
        return self.stocks

    def fetch_quarterly(self, symbol: str) -> pd.DataFrame:
        if symbol in self.broken:
            raise ValueError("Finnomena API error")
        return self.quarterly[symbol]
