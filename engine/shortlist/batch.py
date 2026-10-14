import sqlite3
from collections.abc import Callable
from datetime import date

import pandas as pd

from shortlist import db
from shortlist.config import Config
from shortlist.core import candidates, catalyst, cdc, fair_value, num, quality, risk_reward
from shortlist.sources import FinancialSource, PriceSource, StockInfo

Log = Callable[[str], None]


def default_sources(cfg: Config) -> tuple[PriceSource, FinancialSource]:
    # imported here so tests and the API can load without touching network libraries
    from shortlist.sources.thaifin_source import ThaifinFinancials
    from shortlist.sources.yahoo import YahooPrices

    b = cfg.batch
    return YahooPrices(b.price_period, b.price_chunk_size, b.chunk_delay_seconds), ThaifinFinancials(b.markets)


def run(
    conn: sqlite3.Connection,
    prices_src: PriceSource,
    fin_src: FinancialSource,
    cfg: Config,
    today: date | None = None,
    log: Log = lambda _: None,
) -> int:
    """Raises db.RunInProgress when another batch is running."""
    run_id = db.start_run(conn, cfg.batch.stale_run_minutes)
    execute(conn, run_id, prices_src, fin_src, cfg, today, log)
    return run_id


def execute(
    conn: sqlite3.Connection,
    run_id: int,
    prices_src: PriceSource,
    fin_src: FinancialSource,
    cfg: Config,
    today: date | None = None,
    log: Log = lambda _: None,
) -> None:
    try:
        db.save_run(conn, run_id, collect(prices_src, fin_src, cfg, today or date.today(), log))
    except BaseException as e:
        db.fail_run(conn, run_id, f"{type(e).__name__}: {e}")
        raise


def collect(prices_src: PriceSource, fin_src: FinancialSource, cfg: Config, today: date, log: Log) -> db.RunResults:
    stocks = fin_src.list_stocks()
    log(f"รายชื่อหุ้น {len(stocks)} ตัว")
    prices = prices_src.fetch_prices([s.symbol for s in stocks])
    log(f"ได้ราคา {len(prices)} ตัว")
    failures = {s.symbol: "ไม่มีข้อมูลราคา" for s in stocks if s.symbol not in prices}

    liquidity = {sym: quality.liquidity(p, cfg.liquidity) for sym, p in prices.items()}
    liquid = [sym for sym, r in liquidity.items() if r["passed"]]
    log(f"ผ่าน liquidity {len(liquid)} ตัว ดึงงบ...")
    quarterly: dict[str, pd.DataFrame] = {}
    for sym in liquid:
        try:
            quarterly[sym] = fin_src.fetch_quarterly(sym)
        except Exception as e:
            failures[sym] = f"ดึงงบไม่ได้: {type(e).__name__}: {e}"

    by_symbol = {s.symbol: s for s in stocks}
    pe_by_symbol = {
        sym: (by_symbol[sym].sector, fair_value.current_pe(q, float(prices[sym]["close"].iloc[-1])))
        for sym, q in quarterly.items()
    }
    next_deadline = catalyst.next_statement_deadline(today, cfg.catalyst)

    evaluations = []
    for s in stocks:
        if s.symbol in failures:
            continue
        try:
            evaluations.append(
                evaluate_stock(s, prices[s.symbol], quarterly.get(s.symbol), liquidity[s.symbol],
                               pe_by_symbol, today, next_deadline, cfg)
            )
        except Exception as e:
            failures[s.symbol] = f"ประเมินไม่ได้: {type(e).__name__}: {e}"

    for rank, ev in enumerate(candidates.rank(evaluations, cfg.candidates), start=1):
        ev["candidate_rank"] = rank
    log(f"candidates {sum(e['candidate_rank'] is not None for e in evaluations)} ตัว, fail {len(failures)} ตัว")

    return db.RunResults(
        stocks=stocks,
        prices=prices,
        quarterly=quarterly,
        evaluations=evaluations,
        failures=failures,
        price_date=max((e["price_date"] for e in evaluations), default=None),
    )


def evaluate_stock(
    info: StockInfo,
    prices: pd.DataFrame,
    quarterly: pd.DataFrame | None,
    liquidity: dict,
    pe_by_symbol: dict[str, tuple[str, float | None]],
    today: date,
    next_deadline: date,
    cfg: Config,
) -> dict:
    price = float(prices["close"].iloc[-1])
    cdc_result = cdc.evaluate(prices, cfg.cdc)
    ev = {
        "symbol": info.symbol,
        "name": info.name,
        "sector": info.sector,
        "market": info.market,
        "price": num(price, 2),
        "price_date": prices.index[-1].strftime("%Y-%m-%d"),
        "liquidity": liquidity,
        "quality": None,
        "fair_value": None,
        "cdc": cdc_result,
        "risk_reward": None,
        "hints": catalyst.hints(info.sector, cfg.catalyst),
        "candidate_rank": None,
    }
    # stocks below the liquidity filter have no statements fetched (design D4)
    if quarterly is not None:
        peers = fair_value.peers_for(info.symbol, info.sector, pe_by_symbol)
        fv = fair_value.evaluate(quarterly, price, peers, cfg.fair_value)
        ev["quality"] = quality.evaluate(quarterly, info.sector, cfg.quality)
        ev["fair_value"] = fv
        ev["risk_reward"] = risk_reward.evaluate(
            prices, cdc_result.get("slow"), fv["summary"], today, next_deadline, cfg.risk_reward
        )
    ev["inclusion"] = candidates.inclusion(ev, cfg.candidates)
    return ev
