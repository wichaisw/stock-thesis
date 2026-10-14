"""Per-quarter thaifin close/mkt_cap vs the actual unadjusted close from yfinance."""

import argparse
import warnings

import pandas as pd
import yfinance as yf
from thaifin import Stock

SYMBOLS = ["PTT", "CPALL", "KBANK", "SCAP", "GULF"]
TOLERANCE = 0.02

warnings.filterwarnings("ignore")
pd.set_option("display.width", 250)


def actual_quarter_close(symbol: str, start: str) -> pd.Series:
    px = yf.download(f"{symbol}.BK", start=start, auto_adjust=False, progress=False, actions=False)
    if isinstance(px.columns, pd.MultiIndex):
        px = px.droplevel(1, axis=1)
    q = px["Close"].resample("QE").last()
    q.index = q.index.to_period("Q")
    return q


def compare(symbol: str, shares: float | None, start: str) -> pd.DataFrame:
    raw = Stock(symbol).quarter_dataframe
    df = raw[["close", "mkt_cap"]].apply(pd.to_numeric, errors="coerce")
    # same cut as the engine adapter: rows after the last EPS are upcoming quarters
    df = df.loc[pd.Period(start, "Q") : raw["earning_per_share"].last_valid_index()]
    df["actual_close"] = actual_quarter_close(symbol, start).reindex(df.index)
    df["close_gap"] = df.close / df.actual_close - 1
    df["implied_shares_bn"] = df.mkt_cap / df.close / 1e9
    df["stale_mkt_cap"] = df.mkt_cap.notna() & (df.mkt_cap == df.mkt_cap.shift())
    if shares:
        df["mkt_cap_gap"] = df.mkt_cap / (df.actual_close * shares) - 1
    return df


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("symbols", nargs="*", default=SYMBOLS)
    p.add_argument("--start", default="2021-01-01")
    p.add_argument("--shares", action="append", default=[], help="SYMBOL=count from the SET factsheet")
    args = p.parse_args()
    shares = {k: float(v) for k, v in (s.split("=") for s in args.shares)}

    for symbol in args.symbols:
        df = compare(symbol, shares.get(symbol), args.start)
        gap_cols = [c for c in ("close_gap", "mkt_cap_gap") if c in df]
        bad = (df[gap_cols].abs() > TOLERANCE).any(axis=1) | df.mkt_cap.isna() | df.stale_mkt_cap
        print(f"\n{symbol}: {int(bad.sum())}/{len(df)} quarters outside ±{TOLERANCE:.0%}, missing or stale")
        print(df.round(3).to_string())


if __name__ == "__main__":
    main()
