import sqlite3
import time
from collections.abc import Callable
from datetime import date

import pandas as pd

from shortlist import db
from shortlist.config import Batch, Config
from shortlist.core import candidates, catalyst, cdc, fair_value, num, quality, risk_reward
from shortlist.sources import FinancialSource, PriceSource, StockInfo

Log = Callable[[str], None]

# thaifin wraps every error in a ValueError and yfinance in strings, so the text is all there is (design D2)
NETWORK_ERROR_PATTERNS = (
    "could not resolve host",
    "nodename nor servname",
    "name or service not known",
    "temporary failure in name resolution",
    "errno 8",
    "curl: (6)",
    "curl: (7)",
    "curl: (28)",
    "timed out",
    "connection refused",
    "network is unreachable",
    "connecterror",
    "connecttimeout",
    "readtimeout",
)


def is_network_error(message: str) -> bool:
    m = message.lower()
    return any(p in m for p in NETWORK_ERROR_PATTERNS)


class BatchAborted(Exception):
    """The run stopped early; the message is saved as the run's error and shown in the UI as is."""


class RunGuard:
    """Stops a run when the network is down (N stocks in a row) or when it runs too long."""

    def __init__(self, b: Batch):
        self.max_errors = b.max_consecutive_network_errors
        self.max_minutes = b.max_run_minutes
        self.started = self.lap_started = time.monotonic()
        self.streak = 0

    def record(self, symbol: str, network_error: str | None) -> None:
        """Call once per stock in order; anything but a network error resets the streak."""
        self.streak = self.streak + 1 if network_error else 0
        if self.streak >= self.max_errors:
            raise BatchAborted(
                f"เครือข่ายใช้ไม่ได้: หุ้น {self.streak} ตัวติดกัน fail ด้วย error ของเครือข่าย ล่าสุด {symbol}: {network_error}"
            )

    def lap(self) -> str:
        """Time since the previous lap, for the per-phase log that shows where a slow run went."""
        now = time.monotonic()
        took, self.lap_started = now - self.lap_started, now
        return f"{took:.0f} วินาที"

    def total(self) -> str:
        return f"{time.monotonic() - self.started:.0f} วินาที"

    def check(self, phase: str) -> None:
        if time.monotonic() - self.started > self.max_minutes * 60:
            raise BatchAborted(f"ใช้เวลาเกิน {self.max_minutes:g} นาทีระหว่าง{phase}")


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
    except BatchAborted as e:
        log(str(e))
        db.fail_run(conn, run_id, str(e))
        raise
    except BaseException as e:
        db.fail_run(conn, run_id, f"{type(e).__name__}: {e}")
        raise


def collect(prices_src: PriceSource, fin_src: FinancialSource, cfg: Config, today: date, log: Log) -> db.RunResults:
    guard = RunGuard(cfg.batch)
    try:
        stocks = fin_src.list_stocks()
    except Exception as e:
        # everything waits on this one request, so a network error here needs no streak
        if is_network_error(str(e)):
            raise BatchAborted(f"เครือข่ายใช้ไม่ได้: ดึงรายชื่อหุ้นไม่ได้: {e}") from e
        raise
    log(f"รายชื่อหุ้น {len(stocks)} ตัว ({guard.lap()})")
    guard.check("ดึงราคา")
    prices = prices_src.fetch_prices([s.symbol for s in stocks])
    failures: dict[str, str] = {}
    for s in stocks:
        # yfinance reports an outage as "no data", so only a direct check tells them apart (design D1)
        down = None if s.symbol in prices else prices_src.reachable()
        if s.symbol not in prices:
            failures[s.symbol] = f"ไม่มีข้อมูลราคา: {down}" if down else "ไม่มีข้อมูลราคา"
        guard.record(s.symbol, down)
    log(f"ได้ราคา {len(prices)} ตัว ({guard.lap()})")

    liquidity = {sym: quality.liquidity(p, cfg.liquidity) for sym, p in prices.items()}
    liquid = [sym for sym, r in liquidity.items() if r["passed"]]
    log(f"ผ่าน liquidity {len(liquid)} ตัว ดึงงบ...")
    quarterly: dict[str, pd.DataFrame] = {}
    caps: dict[str, pd.DataFrame] = {}
    for sym in liquid:
        guard.check("ดึงงบและ market cap")
        try:
            quarterly[sym] = fin_src.fetch_quarterly(sym)
        except Exception as e:
            failures[sym] = f"ดึงงบไม่ได้: {type(e).__name__}: {e}"
            guard.record(sym, failures[sym] if is_network_error(str(e)) else None)
            continue
        try:
            caps[sym] = prices_src.fetch_market_caps(sym)
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
            network = reason if is_network_error(reason) else None
        else:
            # an empty history is "no data" unless the source can't be reached at all
            reason = network = prices_src.reachable() if caps[sym].empty else None
        if reason:
            del quarterly[sym]
            caps.pop(sym, None)
            failures[sym] = f"ดึง market cap ไม่ได้: {reason}"
        guard.record(sym, network)

    log(f"ดึงงบและ market cap {len(quarterly)} ตัว ({guard.lap()})")
    guard.check("ประเมิน")
    by_symbol = {s.symbol: s for s in stocks}
    pe_by_symbol = {
        sym: (by_symbol[sym].sector, fair_value.current_pe(q, float(prices[sym]["close"].iloc[-1]), caps[sym]))
        for sym, q in quarterly.items()
    }
    next_deadline = catalyst.next_statement_deadline(today, cfg.catalyst)

    evaluations = []
    for s in stocks:
        if s.symbol in failures:
            continue
        try:
            evaluations.append(
                evaluate_stock(s, prices[s.symbol], quarterly.get(s.symbol), caps.get(s.symbol), liquidity[s.symbol],
                               pe_by_symbol, today, next_deadline, cfg)
            )
        except Exception as e:
            failures[s.symbol] = f"ประเมินไม่ได้: {type(e).__name__}: {e}"

    for rank, ev in enumerate(candidates.rank(evaluations, cfg.candidates), start=1):
        ev["candidate_rank"] = rank
    log(
        f"candidates {sum(e['candidate_rank'] is not None for e in evaluations)} ตัว, fail {len(failures)} ตัว "
        f"(ประเมิน {guard.lap()}, รวม {guard.total()})"
    )

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
    caps: pd.DataFrame | None,
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
        fv = fair_value.evaluate(quarterly, price, peers, cfg.fair_value, caps)
        ev["quality"] = quality.evaluate(quarterly, info.sector, cfg.quality)
        ev["fair_value"] = fv
        ev["risk_reward"] = risk_reward.evaluate(
            prices, cdc_result.get("slow"), fv["summary"], today, next_deadline, cfg.risk_reward
        )
    ev["inclusion"] = candidates.inclusion(ev, cfg.candidates)
    return ev
