"""Source-neutral data shapes the core evaluates; adapters convert into these.

Prices: DataFrame indexed by date with PRICE_COLUMNS, only rows that have a close.
Quarterly: DataFrame indexed by quarter label ("2026Q2"), oldest first, with
QUARTERLY_COLUMNS. Ratios are fractions (0.10 = 10%). The last row is the latest
quarter that has EPS.
Market caps: DataFrame indexed by quarter label with MARKET_CAP_COLUMNS, NaN where the
quarter has no price or share count. Built from traded prices, not dividend- or split-adjusted.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import pandas as pd

PRICE_COLUMNS = ["open", "high", "low", "close", "volume"]
QUARTERLY_COLUMNS = [
    "eps",
    "net_profit",
    "net_profit_yoy",
    "equity",
    "de",
    "ocf",
    "npm",
    "bvps",
    "dividend_yield",
    "close",
]
MARKET_CAP_COLUMNS = ["mkt_cap", "shares"]


@dataclass(frozen=True)
class StockInfo:
    symbol: str
    name: str
    sector: str
    market: str


@runtime_checkable
class PriceSource(Protocol):
    def fetch_prices(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        """Symbols with no data are omitted from the result."""
        ...

    def fetch_market_caps(self, symbol: str) -> pd.DataFrame: ...


@runtime_checkable
class FinancialSource(Protocol):
    def list_stocks(self) -> list[StockInfo]: ...

    def fetch_quarterly(self, symbol: str) -> pd.DataFrame: ...
