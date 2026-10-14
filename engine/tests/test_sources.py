import pytest
import numpy as np
import pandas as pd

from shortlist.sources import FinancialSource, PriceSource
from shortlist.sources.thaifin_source import ThaifinFinancials, to_quarterly, to_stock_info
from shortlist.sources.yahoo import YahooPrices, clean_prices, quarterly_market_cap


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
            "equity": [1e11, 1.1e11, np.nan, np.nan],
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
    assert df["equity"].iloc[-1] == 1.1e11
    assert "roe" not in df.columns
    assert df["net_profit_yoy"].iloc[0] == -0.12


def test_mai_stock_uses_industry_as_sector():
    row = pd.Series({"symbol": "88TH", "name": "x", "industry": "Consumer Products", "sector": "-", "market": "mai"})
    assert to_stock_info(row).sector == "Consumer Products"


def test_market_cap_undoes_split_after_quarter():
    # SCAP: 26.75 traded at end-2022, a 5:1 split in 2023 makes yfinance show 5.35
    close = pd.Series([5.35, 3.52], index=pd.to_datetime(["2022-12-30", "2023-06-30"]))
    splits = pd.Series([5.0], index=pd.to_datetime(["2023-05-26"]))
    shares = pd.Series([1.301e9, 6.506e9], index=pd.to_datetime(["2022-10-01", "2023-06-01"]))
    caps = quarterly_market_cap(close, splits, shares)
    assert caps.loc["2022Q4", "mkt_cap"] == pytest.approx(26.75 * 1.301e9)
    assert caps.loc["2023Q2", "mkt_cap"] == pytest.approx(3.52 * 6.506e9)


def test_market_cap_uses_share_count_at_quarter_end_when_split_mid_quarter():
    # SCAP 2023Q2: ten 1.30B points before the 26 May 5:1 split outvote the one 6.51B point after it
    days = pd.bdate_range("2023-04-03", "2023-06-30")
    close = pd.Series(3.52, index=days)
    splits = pd.Series([5.0], index=pd.to_datetime(["2023-05-26"]))
    before = pd.Series(1.301e9, index=pd.date_range("2023-04-03", "2023-05-25", periods=10))
    shares = pd.concat([before, pd.Series([6.506e9], index=pd.to_datetime(["2023-05-27"]))])
    caps = quarterly_market_cap(close, splits, shares)
    assert caps.loc["2023Q2", "shares"] == 6.506e9


def test_market_cap_ignores_one_day_share_spike():
    close = pd.Series([34.0], index=pd.to_datetime(["2022-06-30"]))
    shares = pd.Series([28.563e9, 29.403e9, 28.563e9], index=pd.to_datetime(["2022-04-01", "2022-05-01", "2022-06-01"]))
    caps = quarterly_market_cap(close, pd.Series(dtype=float), shares)
    assert caps.loc["2022Q2", "shares"] == 28.563e9


def test_no_market_cap_before_first_share_count():
    close = pd.Series([11.3, 5.05, 0.23], index=pd.to_datetime(["2022-12-30", "2023-12-28", "2025-09-30"]))
    shares = pd.Series([2.432e9], index=pd.to_datetime(["2025-05-23"]))
    caps = quarterly_market_cap(close, pd.Series(dtype=float), shares)
    assert caps["mkt_cap"].isna().tolist() == [True, True, False]


def test_no_share_count_at_all_gives_no_market_cap():
    # infrastructure funds (3BBIF, DIF) have prices but no share count on yfinance
    close = pd.Series([10.0], index=pd.to_datetime(["2025-09-30"]))
    caps = quarterly_market_cap(close, pd.Series(dtype=float), pd.Series(dtype=float, index=pd.DatetimeIndex([])))
    assert caps["mkt_cap"].isna().all()
