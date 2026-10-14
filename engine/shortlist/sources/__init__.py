"""Source-neutral data shapes the core evaluates; adapters convert into these.

Prices: DataFrame indexed by date with PRICE_COLUMNS, only rows that have a close.
Quarterly: DataFrame indexed by quarter label ("2026Q2"), oldest first, with
QUARTERLY_COLUMNS. Ratios are fractions (0.10 = 10%). The last row is the latest
quarter that has EPS.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import pandas as pd

PRICE_COLUMNS = ["open", "high", "low", "close", "volume"]
QUARTERLY_COLUMNS = [
    "eps",
    "net_profit",
    "net_profit_yoy",
    "roe",
    "de",
    "ocf",
    "npm",
    "bvps",
    "dividend_yield",
    "close",
]


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


@runtime_checkable
class FinancialSource(Protocol):
    def list_stocks(self) -> list[StockInfo]: ...

    def fetch_quarterly(self, symbol: str) -> pd.DataFrame: ...
