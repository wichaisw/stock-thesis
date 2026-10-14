import numpy as np
import pandas as pd

from shortlist.sources import FinancialSource, PriceSource
from shortlist.sources.thaifin_source import ThaifinFinancials, to_quarterly, to_stock_info
from shortlist.sources.yahoo import YahooPrices, clean_prices


def test_adapters_satisfy_protocols() -> None:
    prices: PriceSource = YahooPrices()
    financials: FinancialSource = ThaifinFinancials(["SET"])
    assert isinstance(prices, PriceSource)
    assert isinstance(financials, FinancialSource)


def test_clean_prices_drops_row_without_close():
    idx = pd.to_datetime(["2026-10-12", "2026-10-13", "2026-10-14"])
    raw = pd.DataFrame(
        {
            "Open": [10, 11, 12],
            "High": [11, 12, 13],
            "Low": [9, 10, 11],
            "Close": [10.5, 11.5, np.nan],
            "Adj Close": [10.5, 11.5, np.nan],
            "Volume": [100, 200, 300],
        },
        index=idx,
    )
    df = clean_prices(raw)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index[-1] == pd.Timestamp("2026-10-13")
    assert df["close"].iloc[-1] == 11.5


def test_quarterly_uses_latest_quarter_with_eps():
    raw = pd.DataFrame(
        {
            "earning_per_share": [0.9, 1.1, np.nan, np.nan],
            "net_profit": [9e9, 11e9, np.nan, np.nan],
            "net_profit_yoy": [-12.0, 8.0, np.nan, np.nan],
            "roe": [14.0, 15.0, np.nan, np.nan],
            "debt_to_equity": [0.8, 0.8, np.nan, np.nan],
            "operating_activities": [5e9, 6e9, np.nan, np.nan],
            "npm": [3.0, 3.5, np.nan, np.nan],
            "book_value_per_share": [10.0, 10.5, np.nan, np.nan],
            "dividend_yield": [3.0, None, 4.0, 4.1],
            "close": [30, 31, 33, 34],
            "gpm": [1, 2, 3, 4],
        },
        index=pd.PeriodIndex(["2026Q1", "2026Q2", "2026Q3", "2026Q4"], freq="Q"),
    )
    df = to_quarterly(raw)
    assert df.index[-1] == "2026Q2"
    assert df["eps"].iloc[-1] == 1.1
    assert df["roe"].iloc[-1] == 0.15
    assert df["net_profit_yoy"].iloc[0] == -0.12


def test_mai_stock_uses_industry_as_sector():
    row = pd.Series({"symbol": "88TH", "name": "x", "industry": "Consumer Products", "sector": "-", "market": "mai"})
    assert to_stock_info(row).sector == "Consumer Products"
