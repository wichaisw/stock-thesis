"""Source-neutral data shapes the core evaluates; adapters convert into these.

Prices: DataFrame indexed by date with PRICE_COLUMNS, only rows that have a close.
Quarterly: DataFrame indexed by quarter label ("2026Q2"), oldest first, with
QUARTERLY_COLUMNS. Ratios are fractions (0.10 = 10%). The last row is the latest
quarter that has EPS.
Market caps: DataFrame indexed by quarter label with MARKET_CAP_COLUMNS, NaN where the
quarter has no price or share count. Built from traded prices, not dividend- or split-adjusted.
dps_ttm is the cash dividend per share (today's share count) gone ex in the 12 months to the
quarter's last trading day, and dividend_yield_ttm is that over the close; stock dividends are not cash.
"""

from dataclasses import dataclass
from datetime import date
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
MARKET_CAP_COLUMNS = ["mkt_cap", "shares", "dps_ttm", "dividend_yield_ttm"]


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

    def reachable(self) -> str | None:
        """None when the source's host answers, else why not. Tells "no data" apart from a network outage."""
        ...


@runtime_checkable
class FinancialSource(Protocol):
    def list_stocks(self) -> list[StockInfo]: ...

    def fetch_quarterly(self, symbol: str) -> pd.DataFrame: ...


INVESTOR_TYPES = ("institution", "proprietary", "foreign", "individual")


@dataclass(frozen=True)
class InvestorFlow:
    """One trading day of SET buy/sell value by investor type, in baht, keyed by INVESTOR_TYPES."""

    date: date
    total_value: float
    buy: dict[str, float]
    sell: dict[str, float]


@runtime_checkable
class InvestorFlowSource(Protocol):
    def fetch_investor_flow(self) -> InvestorFlow:
        """The latest trading day. Raises ValueError when the data fails validation."""
        ...
