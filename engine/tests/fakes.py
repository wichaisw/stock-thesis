from datetime import date

import numpy as np
import pandas as pd

from shortlist.sources import INVESTOR_TYPES, MARKET_CAP_COLUMNS, QUARTERLY_COLUMNS, InvestorFlow, InvestorFlowFetch, MonthlyNetFlow, StockInfo


def price_history(days: int = 120, start: float = 10.0, end: float = 12.0) -> pd.DataFrame:
    close = np.linspace(start, end, days)
    return pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": [5_000_000.0] * days},
        index=pd.bdate_range(end="2026-10-14", periods=days),
    )


def healthy_quarters(n: int = 16) -> pd.DataFrame:
    values = {"eps": 1.0, "net_profit": 1e9, "net_profit_yoy": 0.05, "equity": 1e9 * 4 / 0.14, "de": 0.8, "ocf": 5e8,
              "npm": 0.10, "bvps": 10.0, "dividend_yield": 0.04, "close": 15.0}
    return pd.DataFrame({c: [values[c]] * n for c in QUARTERLY_COLUMNS}, index=[str(q) for q in pd.period_range(end="2026Q2", periods=n, freq="Q")])


def market_caps(quarterly: pd.DataFrame, shares: float = 1e9) -> pd.DataFrame:
    """Market caps and trailing dividends consistent with the quarterly close and yield, as if the share count never changed."""
    return pd.DataFrame(
        {
            "mkt_cap": quarterly["close"] * shares,
            "shares": shares,
            "dps_ttm": quarterly["dividend_yield"] * quarterly["close"],
            "dividend_yield_ttm": quarterly["dividend_yield"],
        },
        index=quarterly.index,
    )[MARKET_CAP_COLUMNS]


class FakePrices:
    def __init__(
        self, prices: dict[str, pd.DataFrame], caps: dict[str, pd.DataFrame] | None = None, unreachable: str | None = None
    ):
        self.prices = prices
        self.caps = caps or {}
        self.unreachable = unreachable

    def fetch_prices(self, symbols: list[str]) -> dict[str, pd.DataFrame]:
        return {s: self.prices[s] for s in symbols if s in self.prices}

    def fetch_market_caps(self, symbol: str) -> pd.DataFrame:
        return self.caps.get(symbol, pd.DataFrame(columns=MARKET_CAP_COLUMNS))

    def reachable(self) -> str | None:
        return self.unreachable


class FakeFinancials:
    def __init__(
        self,
        stocks: list[StockInfo],
        quarterly: dict[str, pd.DataFrame],
        broken: set[str] = frozenset(),
        errors: dict[str, str] | None = None,
    ):
        self.stocks = stocks
        self.quarterly = quarterly
        self.broken = broken
        self.errors = errors or {}  # symbol -> message raised, like thaifin wrapping a network error
        self.calls: list[str] = []

    def list_stocks(self) -> list[StockInfo]:
        return self.stocks

    def fetch_quarterly(self, symbol: str) -> pd.DataFrame:
        self.calls.append(symbol)
        if symbol in self.errors:
            raise ValueError(self.errors[symbol])
        if symbol in self.broken:
            raise ValueError("Finnomena API error")
        return self.quarterly[symbol]


def investor_flow(day: date = date(2026, 10, 14), foreign_buy: float = 50e9) -> InvestorFlow:
    buy = {t: 10e9 for t in INVESTOR_TYPES} | {"foreign": foreign_buy}
    return InvestorFlow(day, sum(buy.values()), buy, dict(buy))


def monthly_net(months: tuple[str, ...] = ("2026-09", "2026-10"), foreign: float = 5e9) -> list[MonthlyNetFlow]:
    return [MonthlyNetFlow(m, {"institution": -foreign, "proprietary": 1e9, "foreign": foreign, "individual": -1e9}) for m in months]


class FakeInvestorFlow:
    """`error` fails the whole page load; `daily_error`/`monthly_error` fail one part's validation."""

    def __init__(
        self,
        flow: InvestorFlow | None = None,
        error: Exception | None = None,
        monthly: list[MonthlyNetFlow] | None = None,
        daily_error: str | None = None,
        monthly_error: str | None = None,
    ):
        self.flow = flow or investor_flow()
        self.monthly = monthly or monthly_net()
        self.error = error
        self.daily_error = daily_error
        self.monthly_error = monthly_error

    def fetch_investor_flow(self) -> InvestorFlowFetch:
        if self.error:
            raise self.error
        return InvestorFlowFetch(
            None if self.daily_error else self.flow,
            None if self.monthly_error else self.monthly,
            self.daily_error,
            self.monthly_error,
        )
