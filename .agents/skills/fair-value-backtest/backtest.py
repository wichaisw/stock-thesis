"""Fetch (or load cached) data, run the fair value backtest and write docs/backtests/fair-value-<date>.md.

Exits with the look-ahead message, writing nothing, when the poison check fails.
"""

import argparse
import pickle
import subprocess
import sys
import time
from datetime import date, datetime
from itertools import batched
from pathlib import Path

import pandas as pd
import yfinance as yf

from shortlist import backtest as bt
from shortlist.config import load_config
from shortlist.core import quality
from shortlist.sources.thaifin_source import ThaifinFinancials
from shortlist.sources.yahoo import YahooPrices, clean_prices

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "engine" / ".cache" / "fv-backtest"
OUT = ROOT / "docs" / "backtests"
PERIOD = "8y"


def cached(path: Path, refresh: bool, fetch):
    if path.exists() and not refresh:
        return pickle.loads(path.read_bytes())
    value = fetch()
    path.write_bytes(pickle.dumps(value))
    return value


def download_prices(symbols: list[str], chunk_size: int, delay: float) -> dict[str, tuple[pd.DataFrame, pd.Series]]:
    out = {}
    for i, chunk in enumerate(batched(symbols, chunk_size)):
        if i:
            time.sleep(delay)
        tickers = [f"{s}.BK" for s in chunk]
        raw = yf.download(tickers, period=PERIOD, group_by="ticker", auto_adjust=False, actions=True,
                          progress=False, threads=True)
        if raw is None or raw.empty:
            continue
        present = set(raw.columns.get_level_values(0))
        for symbol, ticker in zip(chunk, tickers):
            if ticker not in present:
                continue
            r = raw[ticker]
            prices = clean_prices(r)
            if prices.empty:
                continue
            index = pd.DatetimeIndex(r.index).tz_localize(None).normalize()
            prices["adj_close"] = pd.Series(r["Adj Close"].to_numpy(), index=index).reindex(prices.index)
            splits = pd.Series(r["Stock Splits"].to_numpy(), index=index).fillna(0.0)
            out[symbol] = (prices, splits)
        print(f"ราคา {min((i + 1) * chunk_size, len(symbols))}/{len(symbols)}", file=sys.stderr)
    return out


def liquid_on_any(px: pd.DataFrame, dates: list[pd.Timestamp], cfg) -> bool:
    """Only these stocks get statements fetched, like the batch (design D4 of the shortlist)."""
    return any(len(c := px[px.index <= t]) and quality.liquidity(c, cfg)["passed"] for t in dates)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--refresh", action="store_true", help="ดึงข้อมูลใหม่ทั้งหมด ไม่ใช้ cache")
    p.add_argument("--start", default="2021Q1")
    p.add_argument("--end", default="2026Q2")
    args = p.parse_args()

    cfg = load_config()
    CACHE.mkdir(parents=True, exist_ok=True)
    stocks = cached(CACHE / "stocks.pkl", args.refresh,
                    lambda: ThaifinFinancials(cfg.batch.markets).list_stocks())
    b = cfg.batch
    prices = cached(CACHE / "prices.pkl", args.refresh,
                    lambda: download_prices([s.symbol for s in stocks], b.price_chunk_size, b.chunk_delay_seconds))
    cache_date = date.fromtimestamp((CACHE / "prices.pkl").stat().st_mtime).isoformat()
    dates = bt.quarter_ends(args.start, args.end)

    ever_liquid = [s for s in stocks if s.symbol in prices and liquid_on_any(prices[s.symbol][0], dates, cfg.liquidity)]
    print(f"หุ้น {len(stocks)} ตัว มีราคา {len(prices)} ตัว เคยผ่าน liquidity {len(ever_liquid)} ตัว", file=sys.stderr)

    fin, yahoo = ThaifinFinancials(b.markets), YahooPrices(history_period=PERIOD)
    data: dict[str, bt.StockData] = {}
    failures: dict[str, str] = {}
    for n, s in enumerate(ever_liquid, 1):
        path = CACHE / f"{s.symbol}.pkl"
        if path.exists() and not args.refresh:
            quarterly, caps = pickle.loads(path.read_bytes())
        else:
            # failures are not cached, so the next run retries only the ones missing
            try:
                quarterly = fin.fetch_quarterly(s.symbol)
            except Exception as e:
                failures[s.symbol] = f"ดึงงบไม่ได้: {type(e).__name__}: {e}"
                continue
            try:
                caps = yahoo.fetch_market_caps(s.symbol)
            except Exception as e:
                failures[s.symbol] = f"ดึง market cap ไม่ได้: {type(e).__name__}: {e}"
                continue
            if caps.empty:
                failures[s.symbol] = "ดึง market cap ไม่ได้: ไม่มีข้อมูล"
                continue
            path.write_bytes(pickle.dumps((quarterly, caps)))
            if n % 25 == 0:
                print(f"งบและ market cap {n}/{len(ever_liquid)}", file=sys.stderr)
        px, splits = prices[s.symbol]
        data[s.symbol] = bt.StockData(info=s, prices=px, splits=splits, quarterly=quarterly, caps=caps)

    excluded = bt.excluded(data, args.start, args.end, cfg.fair_value.structure_change_threshold)
    kept = {k: v for k, v in data.items() if k not in excluded}

    try:
        poisoned = bt.poison_check(kept, dates, cfg)
    except bt.LookAhead as e:
        sys.exit(f"{e}\nหยุด ไม่เขียนไฟล์ผล: แก้ bug ที่ตัดข้อมูลก่อน")

    rows, skipped = [], {}
    for t in dates:
        r, skipped[t] = bt.evaluate_date(kept, t, cfg)
        rows += r
    df = bt.with_outcomes(pd.DataFrame(rows), {k: v.prices for k, v in kept.items()})
    md = bt.report(
        meta={
            "run_date": date.today().isoformat(),
            "commit": git("rev-parse", "--short", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--", "engine")),
            "cache_date": cache_date,
        },
        cfg=cfg, dates=dates, universe=len(data), excluded=excluded, failures=failures, skipped=skipped,
        poisoned=poisoned, rows=df, result=bt.metrics(df, cfg.candidates.min_median_mos),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"fair-value-{date.today().isoformat()}.md"
    out.write_text(md)
    print(md)
    print(f"เขียน {out.relative_to(ROOT)} ({datetime.now():%H:%M:%S})", file=sys.stderr)


if __name__ == "__main__":
    main()
