import pandas as pd
from thaifin import Stock, Stocks

from shortlist.sources import QUARTERLY_COLUMNS, StockInfo

FIELD_MAP = {
    "earning_per_share": "eps",
    "net_profit": "net_profit",
    "net_profit_yoy": "net_profit_yoy",
    "roe": "roe",
    "debt_to_equity": "de",
    "operating_activities": "ocf",
    "npm": "npm",
    "book_value_per_share": "bvps",
    "dividend_yield": "dividend_yield",
    "close": "close",
}
PERCENT_FIELDS = ["net_profit_yoy", "roe", "npm", "dividend_yield"]


def to_quarterly(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[list(FIELD_MAP)].rename(columns=FIELD_MAP)[QUARTERLY_COLUMNS]
    df = df.apply(pd.to_numeric, errors="coerce")
    df[PERCENT_FIELDS] = df[PERCENT_FIELDS] / 100
    df.index = [str(q) for q in raw.index]
    df.index.name = "quarter"
    # thaifin appends upcoming quarters that only carry price ratios
    last = df["eps"].last_valid_index()
    return df.loc[:last] if last is not None else df.iloc[0:0]


def to_stock_info(row: pd.Series) -> StockInfo:
    # mai stocks have no sector ("-"), so their industry is the closest peer group
    sector = row["sector"] if row["sector"] not in ("", "-") else row["industry"]
    return StockInfo(symbol=row["symbol"], name=row["name"], sector=sector, market=row["market"])


class ThaifinFinancials:
    def __init__(self, markets: list[str]):
        self.markets = markets

    def list_stocks(self) -> list[StockInfo]:
        df = Stocks.list_with_names()
        df = df[df["market"].isin(self.markets)]
        return [to_stock_info(row) for _, row in df.iterrows()]

    def fetch_quarterly(self, symbol: str) -> pd.DataFrame:
        return to_quarterly(Stock(symbol).quarter_dataframe)
