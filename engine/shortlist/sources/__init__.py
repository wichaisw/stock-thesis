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


MAX_FLOW_SUM_GAP = 0.01


def check_investor_flow(flow: InvestorFlow) -> InvestorFlow:
    """Raises ValueError when the buy or sell sum of the 4 types is more than 1% off the total. Returns `flow`."""
    for side, values in (("ซื้อ", flow.buy), ("ขาย", flow.sell)):
        if abs(sum(values.values()) - flow.total_value) > MAX_FLOW_SUM_GAP * flow.total_value:
            raise ValueError(f"ผลรวมมูลค่า{side} {sum(values.values()):,.0f} ต่างจากมูลค่ารวม {flow.total_value:,.0f} เกิน 1%")
    return flow


@dataclass(frozen=True)
class MonthlyNetFlow:
    """One month of SET net value (buy − sell) by investor type in baht, cumulative from the first month of the set."""

    month: str  # "2026-10"
    net: dict[str, float]


@dataclass(frozen=True)
class InvestorFlowFetch:
    """Both parts come from one page load but are validated apart, so one can be kept when the other fails.
    A failed part is None with its reason in the matching *_error."""

    daily: InvestorFlow | None
    monthly: list[MonthlyNetFlow] | None
    daily_error: str | None = None
    monthly_error: str | None = None


@runtime_checkable
class InvestorFlowHistorySource(Protocol):
    def fetch_history(self) -> list[InvestorFlow]:
        """Every day the source still lists, oldest first. Raises when a page or a day cannot be read or validated."""
        ...


@runtime_checkable
class InvestorFlowSource(Protocol):
    def fetch_investor_flow(self) -> InvestorFlowFetch:
        """The latest trading day and the 1-year monthly net chart. Raises when the page cannot be fetched at all."""
        ...

