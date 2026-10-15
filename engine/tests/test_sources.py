import json
from datetime import date
from pathlib import Path

import pytest
import numpy as np
import pandas as pd

from shortlist.sources import QUARTERLY_COLUMNS, FinancialSource, InvestorFlowSource, PriceSource
from shortlist.sources.preferred import PreferredStatements
from shortlist.sources.set_investor import SetInvestorFlow, to_investor_flow, to_monthly_net
from shortlist.sources.thaifin_source import ThaifinFinancials, to_quarterly, to_stock_info
from shortlist.sources.yahoo import YahooPrices, clean_prices, fetch_statements, quarterly_market_cap, to_statements
from tests.fakes import FakeFinancials


def test_adapters_satisfy_protocols() -> None:
    prices: PriceSource = YahooPrices()
    financials: FinancialSource = ThaifinFinancials(["SET"])
    assert isinstance(prices, PriceSource)
    assert isinstance(financials, FinancialSource)
    assert isinstance(PreferredStatements(financials, fetch_statements), FinancialSource)


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


def quarter_ends(*days: str) -> pd.DatetimeIndex:
    return pd.to_datetime(list(days))


def test_trailing_yield_sums_cash_dividends_of_the_last_12_months():
    # paid twice a year: 0.80 in March and 1.30 in September, close 35.00 at year end
    close = pd.Series([35.0], index=quarter_ends("2025-12-30"))
    divs = pd.Series([0.8, 1.3], index=quarter_ends("2025-03-06", "2025-09-28"))
    caps = quarterly_market_cap(close, pd.Series(dtype=float), pd.Series([1e9], index=quarter_ends("2025-01-01")), divs)
    assert caps.loc["2025Q4", "dps_ttm"] == pytest.approx(2.1)
    assert caps.loc["2025Q4", "dividend_yield_ttm"] == pytest.approx(0.06)


def test_quarter_without_xd_still_counts_the_previous_12_months():
    close = pd.Series([20.0, 20.0], index=quarter_ends("2025-03-31", "2025-06-30"))
    divs = pd.Series([1.0], index=quarter_ends("2025-03-06"))
    caps = quarterly_market_cap(close, pd.Series(dtype=float), pd.Series(dtype=float), divs)
    assert caps.loc["2025Q2", "dividend_yield_ttm"] == pytest.approx(0.05)


def test_stock_dividend_counts_only_its_cash_part():
    # DITTO 2022: a 1.2 "split" (stock dividend) with 0.0093 cash; yfinance keeps them in separate columns
    close = pd.Series([50.0], index=quarter_ends("2022-06-30"))
    splits = pd.Series([1.2], index=quarter_ends("2022-03-15"))
    divs = pd.Series([0.0093], index=quarter_ends("2022-03-15"))
    caps = quarterly_market_cap(close, splits, pd.Series(dtype=float), divs)
    assert caps.loc["2022Q2", "dps_ttm"] == pytest.approx(0.0093)


def test_yield_is_unchanged_by_a_later_split():
    # 1.00 paid at a 20.00 close, then a 2:1 split: yfinance shows 0.50 and 10.00 for that day
    close = pd.Series([10.0, 5.0], index=quarter_ends("2024-06-28", "2025-06-30"))
    splits = pd.Series([2.0], index=quarter_ends("2025-01-15"))
    divs = pd.Series([0.5], index=quarter_ends("2024-06-10"))
    caps = quarterly_market_cap(close, splits, pd.Series(dtype=float), divs)
    assert caps.loc["2024Q2", "dividend_yield_ttm"] == pytest.approx(0.05)


def test_no_cash_dividend_gives_zero_yield():
    close = pd.Series([10.0, 11.0], index=quarter_ends("2025-03-31", "2025-06-30"))
    caps = quarterly_market_cap(close, pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float))
    assert (caps["dividend_yield_ttm"] == 0).all() and (caps["dps_ttm"] == 0).all()


def test_price_source_reachable_on_any_http_reply(monkeypatch):
    import urllib.error
    from email.message import Message

    from shortlist.sources import yahoo

    class Reply:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(yahoo.urllib.request, "urlopen", lambda url, timeout: Reply())
    assert YahooPrices().reachable() is None

    def too_many(url, timeout):
        raise urllib.error.HTTPError(url, 429, "Too Many Requests", Message(), None)

    # rate limiting still proves the network reaches Yahoo
    monkeypatch.setattr(yahoo.urllib.request, "urlopen", too_many)
    assert YahooPrices().reachable() is None


def test_price_source_unreachable_when_dns_fails(monkeypatch):
    import urllib.error

    from shortlist.sources import yahoo

    def dns_down(url, timeout):
        raise urllib.error.URLError(OSError(8, "nodename nor servname provided, or not known"))

    monkeypatch.setattr(yahoo.urllib.request, "urlopen", dns_down)
    msg = YahooPrices().reachable()
    assert msg.startswith("เชื่อมต่อแหล่งราคาไม่ได้: ")
    assert "nodename nor servname" in msg


INVESTOR_FIXTURE = Path(__file__).parent / "fixtures" / "investor_type_2026-10-14.json"


def investor_raw() -> dict:
    return json.loads(INVESTOR_FIXTURE.read_text())


def test_investor_flow_adapter_satisfies_protocol() -> None:
    assert isinstance(SetInvestorFlow(), InvestorFlowSource)


def test_investor_flow_parses_set_fixture():
    flow = to_investor_flow(investor_raw())
    assert flow.date == date(2026, 10, 14)
    assert flow.total_value == pytest.approx(80_644_591_129.58)
    assert flow.buy["foreign"] == pytest.approx(53_230_152_423.44)
    assert flow.sell["foreign"] == pytest.approx(47_539_165_411.55)
    assert set(flow.buy) == set(flow.sell) == {"institution", "proprietary", "foreign", "individual"}


def test_investor_flow_rejects_missing_type():
    raw = investor_raw()
    raw["investors"] = [i for i in raw["investors"] if i["type"] != "proprietary"]
    with pytest.raises(ValueError, match="proprietary"):
        to_investor_flow(raw)


def test_investor_flow_rejects_sum_off_total():
    raw = investor_raw()
    raw["investors"][0]["sellValue"] *= 3
    with pytest.raises(ValueError, match="ขาย"):
        to_investor_flow(raw)


def chart_raw() -> list[dict]:
    return json.loads((Path(__file__).parent / "fixtures" / "investor_type_chart_1y_2026-10-15.json").read_text())


def test_monthly_net_parses_13_points_of_the_set_fixture():
    points = to_monthly_net(chart_raw())
    assert [p.month for p in points][::12] == ["2025-10", "2026-10"] and len(points) == 13
    # settrade.com shows -113,706 million for institution at Oct 69
    assert points[-1].net["institution"] == pytest.approx(-113_706_161_059.01)


def test_monthly_net_rejects_a_point_missing_a_type():
    raw = chart_raw()
    del raw[3]["proprietary"]
    with pytest.raises(ValueError, match="2026-01.*proprietary"):
        to_monthly_net(raw)


def test_monthly_net_rejects_nets_not_summing_to_zero():
    raw = chart_raw()
    raw[5]["foreign"] += 1.5e6
    with pytest.raises(ValueError, match="2026-03"):
        to_monthly_net(raw)
    raw[5]["foreign"] -= 1.4e6  # 0.1 million off is rounding, kept
    assert len(to_monthly_net(raw)) == 13


def test_monthly_net_rejects_a_repeated_month():
    raw = chart_raw()
    raw.append(raw[-1])
    with pytest.raises(ValueError, match="2026-10"):
        to_monthly_net(raw)


def yahoo_statements(currency: str | None = "THB"):
    dates = pd.to_datetime(["2026-06-30", "2026-03-31", "2025-12-31"])
    income = pd.DataFrame(
        [[7.5e9, 9.1e9, 7.3e9], [7.4e9, 9.0e9, 7.1e9]], index=["Net Income", "Net Income Common Stockholders"], columns=dates
    )
    balance = pd.DataFrame([[141e9, np.nan, 138e9]], index=["Stockholders Equity"], columns=dates)
    return income, balance, currency


def test_statements_are_indexed_by_quarter_oldest_first():
    df = to_statements(*yahoo_statements())
    assert list(df.index) == ["2025Q4", "2026Q1", "2026Q2"]
    assert df.loc["2026Q2", "net_profit"] == 7.5e9  # Net Income, not the common-stockholders row
    assert df.loc["2026Q2", "equity"] == 141e9
    assert np.isnan(df.loc["2026Q1", "equity"])


@pytest.mark.parametrize("currency", ["USD", None])
def test_statements_not_in_baht_are_dropped(currency):
    assert to_statements(*yahoo_statements(currency)).empty


def test_statements_fetch_error_gives_empty(monkeypatch):
    def boom(_):
        raise RuntimeError("HTTP 429")

    monkeypatch.setattr("shortlist.sources.yahoo.yf.Ticker", boom)
    assert fetch_statements("PTT").empty


def thaifin_quarters(labels: list[str]) -> pd.DataFrame:
    n = len(labels)
    return pd.DataFrame({c: [1.0] * n for c in QUARTERLY_COLUMNS}, index=labels)


QUARTERS_5Y = [f"{y}Q{q}" for y in range(2021, 2027) for q in range(1, 5)][:22]  # 2021Q1–2026Q2


def test_preferred_statements_win_on_the_quarters_they_have():
    recent = QUARTERS_5Y[-5:]  # 2025Q2–2026Q2
    yahoo = pd.DataFrame({"net_profit": 2.0, "equity": 3.0}, index=recent)
    src = PreferredStatements(FakeFinancials([], {"PTT": thaifin_quarters(QUARTERS_5Y)}), lambda _: yahoo)
    df = src.fetch_quarterly("PTT")
    assert (df.loc[recent, ["net_profit", "equity"]].values == [2.0, 3.0]).all()
    assert (df.loc[QUARTERS_5Y[:-5], ["net_profit", "equity"]] == 1.0).all().all()
    assert (df[["eps", "bvps", "de"]] == 1.0).all().all()  # other fields stay from thaifin
    assert src.overlaid == {"PTT"}


def test_preferred_gap_falls_back_to_base():
    yahoo = pd.DataFrame({"net_profit": [2.0], "equity": [np.nan]}, index=["2026Q1"])
    df = PreferredStatements(FakeFinancials([], {"PTT": thaifin_quarters(["2026Q1"])}), lambda _: yahoo).fetch_quarterly("PTT")
    assert (df.loc["2026Q1", "net_profit"], df.loc["2026Q1", "equity"]) == (2.0, 1.0)


def test_preferred_quarter_missing_from_base_is_not_added():
    yahoo = pd.DataFrame({"net_profit": [2.0, 2.0], "equity": [3.0, 3.0]}, index=["2026Q2", "2026Q3"])
    df = PreferredStatements(FakeFinancials([], {"PTT": thaifin_quarters(["2026Q2"])}), lambda _: yahoo).fetch_quarterly("PTT")
    assert list(df.index) == ["2026Q2"]


def test_preferred_error_or_empty_keeps_base():
    def boom(_):
        raise RuntimeError("HTTP 429")

    base = thaifin_quarters(["2026Q2"])
    for fetch in (boom, lambda _: pd.DataFrame(columns=["net_profit", "equity"])):
        src = PreferredStatements(FakeFinancials([], {"PTT": base}), fetch)
        assert src.fetch_quarterly("PTT").equals(base)
        assert src.overlaid == set()


def test_preferred_equal_to_base_still_counts_as_used():
    base = thaifin_quarters(["2026Q2"])
    src = PreferredStatements(FakeFinancials([], {"PTT": base}), lambda _: pd.DataFrame({"net_profit": [1.0]}, index=["2026Q2"]))
    src.fetch_quarterly("PTT")
    assert src.overlaid == {"PTT"}
