import sqlite3
import time
from datetime import date
from collections.abc import Callable

import pandas as pd

from shortlist import db
from shortlist.config import Batch, Config
from shortlist.core import candidates, catalyst, cdc, fair_value, num, quality, risk_reward
from shortlist.sources import (
    INVESTOR_TYPES,
    FinancialSource,
    InvestorFlowHistorySource,
    InvestorFlowSource,
    PriceSource,
    StockInfo,
)

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


def default_sources(cfg: Config) -> tuple[PriceSource, FinancialSource, InvestorFlowSource]:
    # imported here so tests and the API can load without touching network libraries
    from shortlist.sources.preferred import PreferredStatements
    from shortlist.sources.set_investor import SetInvestorFlow
    from shortlist.sources.thaifin_source import ThaifinFinancials
    from shortlist.sources.yahoo import YahooPrices, fetch_statements

    b = cfg.batch
    return (
        YahooPrices(b.price_period, b.price_chunk_size, b.chunk_delay_seconds, threads=b.price_threads,
                    retry_delay_seconds=b.price_retry_delay_seconds),
        PreferredStatements(ThaifinFinancials(b.markets), fetch_statements),
        SetInvestorFlow(),
    )


def run(
    conn: sqlite3.Connection,
    prices_src: PriceSource,
    fin_src: FinancialSource,
    cfg: Config,
    log: Log = lambda _: None,
    flow_src: InvestorFlowSource | None = None,
) -> int:
    """Raises db.RunInProgress when another batch is running."""
    run_id = db.start_run(conn, cfg.batch.stale_run_minutes)
    execute(conn, run_id, prices_src, fin_src, cfg, log, flow_src)
    return run_id


def execute(
    conn: sqlite3.Connection,
    run_id: int,
    prices_src: PriceSource,
    fin_src: FinancialSource,
    cfg: Config,
    log: Log = lambda _: None,
    flow_src: InvestorFlowSource | None = None,
) -> None:
    try:
        db.save_run(conn, run_id, collect(prices_src, fin_src, cfg, log))
    except BatchAborted as e:
        log(str(e))
        db.fail_run(conn, run_id, str(e))
        raise
    except BaseException as e:
        db.fail_run(conn, run_id, f"{type(e).__name__}: {e}")
        raise
    if flow_src:
        record_investor_flow(conn, flow_src, log)


def record_investor_flow(conn: sqlite3.Connection, src: InvestorFlowSource, log: Log) -> str | None:
    """Never raises: a batch run must not fail on this (design D3). Daily and monthly parts are saved apart (D5).
    Returns why the daily part was not saved, else None."""
    started = time.monotonic()
    try:
        got = src.fetch_investor_flow()
    except Exception as e:
        error = f"ดึงข้อมูลประเภทนักลงทุนไม่ได้: {type(e).__name__}: {e}"
        log(error)
        return error
    if got.monthly is None:
        log(f"กราฟประเภทนักลงทุนรายเดือนไม่ผ่านการตรวจ ไม่เก็บ: {got.monthly_error}")
    else:
        db.save_monthly_net(conn, got.monthly)
        log(f"เก็บกราฟประเภทนักลงทุนรายเดือน {len(got.monthly)} จุด ถึงเดือน {got.monthly[-1].month}")
    if got.daily is None:
        error = f"ข้อมูลประเภทนักลงทุนไม่ผ่านการตรวจ ไม่เก็บ: {got.daily_error}"
        log(error)
        return error
    db.save_investor_flow(conn, got.daily)
    log(f"เก็บข้อมูลประเภทนักลงทุนของวันที่ {got.daily.date} ({time.monotonic() - started:.0f} วินาที)")
    return None


# the backfill source rounds to 0.01 million baht
MAX_BACKFILL_GAP = 10_000


def backfill_investor_flow(conn: sqlite3.Connection, src: InvestorFlowHistorySource) -> int:
    """Adds the days not stored yet (daily-flow-backfill-chart D3). Raises ValueError and writes nothing when any day
    disagrees with a closing day already fetched from SET, or no such day overlaps. Returns how many days were added."""
    flows = src.fetch_history()
    closing = {r["date"]: r for r in db.investor_flow(conn, limit=10_000) if r["source"] == "set" and not r["intraday"]}
    compared, errors = 0, []
    for f in flows:
        row = closing.get(f.date.isoformat())
        if row is None:
            continue
        compared += 1
        for t in INVESTOR_TYPES:
            for side, side_th, value in (("buy", "ซื้อ", f.buy[t]), ("sell", "ขาย", f.sell[t])):
                if abs(value - row[f"{t}_{side}"]) > MAX_BACKFILL_GAP:
                    errors.append(f"{f.date} {t} {side_th}: InfoQuest {value / 1e6:,.2f} SET {row[f'{t}_{side}'] / 1e6:,.2f} ล้านบาท")
    if errors:
        raise ValueError("ไม่ตรงกับข้อมูลจาก SET ไม่เขียนข้อมูล: " + "; ".join(errors))
    if not compared:
        raise ValueError("ยังไม่มีข้อมูลปิดตลาดจาก SET ในช่วงเดียวกันให้เทียบ ไม่เขียนข้อมูล")
    return db.backfill_investor_flow(conn, flows, "infoquest")


def collect(prices_src: PriceSource, fin_src: FinancialSource, cfg: Config, log: Log) -> db.RunResults:
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
    if retry := getattr(prices_src, "last_retry", None):
        log(f"ดึงราคาซ้ำ {retry[0]} ตัว ได้คืน {retry[1]} ตัว")

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
    # a sudden drop to 0 means yfinance renamed a row and everything fell back to thaifin silently
    if (overlaid := getattr(fin_src, "overlaid", None)) is not None:
        log(f"ใช้กำไรและส่วนผู้ถือหุ้นจาก yfinance {len(overlaid & quarterly.keys())} ตัว")
    guard.check("ประเมิน")
    by_symbol = {s.symbol: s for s in stocks}
    pe_by_symbol = {
        sym: (by_symbol[sym].sector, fair_value.current_pe(q, float(prices[sym]["close"].iloc[-1]), caps[sym]))
        for sym, q in quarterly.items()
    }

    evaluations = []
    for s in stocks:
        if s.symbol in failures:
            continue
        try:
            evaluations.append(
                evaluate_stock(s, prices[s.symbol], quarterly.get(s.symbol), caps.get(s.symbol), liquidity[s.symbol],
                               pe_by_symbol, cfg)
            )
        except Exception as e:
            failures[s.symbol] = f"ประเมินไม่ได้: {type(e).__name__}: {e}"

    for rank, ev in enumerate(candidates.rank(evaluations, cfg.candidates), start=1):
        ev["candidate_rank"] = rank
    # needs every stock's latest bar first: without an SET holiday calendar, the newest bar in the run is the reference
    price_date = max((e["price_date"] for e in evaluations), default=None)
    for ev in evaluations:
        ev["stale_price"] = ev["price_date"] < price_date
        # tags set after ranking, so they cannot change the list or its order (add-risk-flags)
        if (q := quarterly.get(ev["symbol"])) is not None:
            reported = quality.reported_quarters(q)[0]
            ev["earnings_due"] = (
                catalyst.earnings_due(str(reported.index[-1]), date.fromisoformat(price_date), cfg.flags.earnings_due_days,
                                      cfg.catalyst)
                if len(reported) else {"flag": False, "reason": None}
            )
    log(
        f"candidates {sum(e['candidate_rank'] is not None for e in evaluations)} ตัว, fail {len(failures)} ตัว, "
        f"ราคาไม่อัปเดต {sum(e['stale_price'] for e in evaluations)} ตัว (ประเมิน {guard.lap()}, รวม {guard.total()})"
    )

    return db.RunResults(
        stocks=stocks,
        prices=prices,
        quarterly=quarterly,
        evaluations=evaluations,
        failures=failures,
        price_date=price_date,
    )


def evaluate_stock(
    info: StockInfo,
    prices: pd.DataFrame,
    quarterly: pd.DataFrame | None,
    caps: pd.DataFrame | None,
    liquidity: dict,
    pe_by_symbol: dict[str, tuple[str, float | None]],
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
        # the run's threshold travels with the gate, like liquidity.threshold, so the detail page shows what was applied
        fv["gate"] = fair_value.gate(fv["items"], cfg.candidates.gate_methods) | {"min_mos": cfg.candidates.min_gate_mos}
        ev["quality"] = quality.evaluate(quarterly, info.sector, cfg.quality)
        ev["quality"]["profit_jump"] = quality.profit_jump(quality.reported_quarters(quarterly)[0], cfg.flags.profit_jump_ratio)
        ev["fair_value"] = fv
        ev["risk_reward"] = risk_reward.evaluate(prices, cdc_result.get("slow"), fv, cfg.risk_reward)
    ev["inclusion"] = candidates.inclusion(ev, cfg.candidates)
    return ev
