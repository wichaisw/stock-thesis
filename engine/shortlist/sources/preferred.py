from collections.abc import Callable

import pandas as pd

from shortlist.sources import FinancialSource, StockInfo


def overlay(base: pd.DataFrame, preferred: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Preferred values win, but only on quarters `base` already has and cells `preferred` has a value for (design D2).
    The flag says whether any preferred value landed, even one equal to the base value."""
    aligned = preferred.reindex(index=base.index, columns=preferred.columns.intersection(base.columns))
    out = base.copy()
    out.update(aligned)
    return out, bool(aligned.notna().any().any())


class PreferredStatements:
    """A FinancialSource whose net profit and equity come from another source first (design D1)."""

    def __init__(self, base: FinancialSource, fetch_statements: Callable[[str], pd.DataFrame]):
        self.base = base
        self.fetch_statements = fetch_statements
        self.overlaid: set[str] = set()  # symbols that got at least one preferred value, for the batch log

    def list_stocks(self) -> list[StockInfo]:
        return self.base.list_stocks()

    def fetch_quarterly(self, symbol: str) -> pd.DataFrame:
        base = self.base.fetch_quarterly(symbol)
        try:
            preferred = self.fetch_statements(symbol)
        except Exception:
            return base  # a supplement failing never fails the stock (design D5)
        out, used = overlay(base, preferred)
        if used:
            self.overlaid.add(symbol)
        return out
