import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from shortlist.sources import INVESTOR_TYPES, QUARTERLY_COLUMNS, InvestorFlow, NetFlow, StockInfo

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "shortlist.db"

FLOW_COLUMNS = [f"{t}_{side}" for t in INVESTOR_TYPES for side in ("buy", "sell")]
# SET closes 16:30 and the ATC round ends around 16:40; anything fetched earlier on that day is intraday
MARKET_CLOSED_AT = time(17, tzinfo=ZoneInfo("Asia/Bangkok"))

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS stocks (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT NOT NULL,
    market TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prices_daily (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL NOT NULL, volume REAL,
    PRIMARY KEY (symbol, date)
);
CREATE TABLE IF NOT EXISTS financials_quarterly (
    symbol TEXT NOT NULL,
    quarter TEXT NOT NULL,
    {", ".join(f"{c} REAL" for c in QUARTERLY_COLUMNS)},
    PRIMARY KEY (symbol, quarter)
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    price_date TEXT,
    total INTEGER,
    succeeded INTEGER,
    failed INTEGER,
    error TEXT
);
CREATE TABLE IF NOT EXISTS run_failures (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    symbol TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY (run_id, symbol)
);
CREATE TABLE IF NOT EXISTS evaluations (
    run_id INTEGER NOT NULL REFERENCES runs(id),
    symbol TEXT NOT NULL,
    candidate_rank INTEGER,
    result TEXT NOT NULL,
    PRIMARY KEY (run_id, symbol)
);
CREATE TABLE IF NOT EXISTS manual_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    text TEXT NOT NULL
);
-- kept across runs: SET only serves the latest day, so this is the only history there is
CREATE TABLE IF NOT EXISTS investor_flow (
    date TEXT PRIMARY KEY,
    total_value REAL NOT NULL,
    {", ".join(f"{c} REAL NOT NULL" for c in FLOW_COLUMNS)},
    fetched_at TEXT NOT NULL
);
-- net-only backfill from siamchart (design D5); local_institution_net includes proprietary
CREATE TABLE IF NOT EXISTS investor_flow_net (
    date TEXT PRIMARY KEY,
    local_institution_net REAL NOT NULL,
    foreign_net REAL NOT NULL,
    individual_net REAL NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    overrides TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class RunInProgress(Exception):
    pass


@dataclass
class RunResults:
    stocks: list[StockInfo]
    prices: dict[str, pd.DataFrame]
    quarterly: dict[str, pd.DataFrame]
    # each has "symbol" and "candidate_rank" (None when not a candidate)
    evaluations: list[dict]
    failures: dict[str, str]
    price_date: str | None


def connect(path: Path | str = DEFAULT_PATH) -> sqlite3.Connection:
    # FastAPI may open a request-scoped connection on one thread and use it on another;
    # each connection still serves only one request at a time
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # financials_quarterly is rewritten every run, so a column change just recreates it
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(financials_quarterly)")]
    if cols and cols[2:] != QUARTERLY_COLUMNS:
        conn.execute("DROP TABLE financials_quarterly")
    conn.executescript(SCHEMA)
    return conn


def _now() -> datetime:
    return datetime.now().astimezone()


def start_run(conn: sqlite3.Connection, stale_minutes: int, now: datetime | None = None) -> int:
    now = now or _now()
    cutoff = (now - timedelta(minutes=stale_minutes)).isoformat()
    # IMMEDIATE takes the write lock so two starters cannot both see "no running run"
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE runs SET status='failed', finished_at=?, error='ค้างเกินเวลา ถือว่า process ตาย' "
            "WHERE status='running' AND started_at < ?",
            (now.isoformat(), cutoff),
        )
        if conn.execute("SELECT 1 FROM runs WHERE status='running'").fetchone():
            raise RunInProgress("มี batch กำลังรันอยู่")
        run_id = conn.execute(
            "INSERT INTO runs (status, started_at) VALUES ('running', ?)", (now.isoformat(),)
        ).lastrowid
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    assert run_id is not None
    return run_id


def fail_run(conn: sqlite3.Connection, run_id: int, error: str) -> None:
    with conn:
        conn.execute(
            "UPDATE runs SET status='failed', finished_at=?, error=? WHERE id=?",
            (_now().isoformat(), error, run_id),
        )


def save_run(conn: sqlite3.Connection, run_id: int, results: RunResults) -> None:
    """Writes everything in one transaction so readers never see a half-finished run."""
    with conn:
        conn.execute("DELETE FROM stocks")
        conn.executemany(
            "INSERT INTO stocks VALUES (?, ?, ?, ?)",
            [(s.symbol, s.name, s.sector, s.market) for s in results.stocks],
        )
        conn.execute("DELETE FROM prices_daily")
        conn.executemany(
            "INSERT INTO prices_daily VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (symbol, d.strftime("%Y-%m-%d"), *(_num(v) for v in row))
                for symbol, df in results.prices.items()
                for d, row in zip(df.index, df[["open", "high", "low", "close", "volume"]].itertuples(index=False))
            ],
        )
        conn.execute("DELETE FROM financials_quarterly")
        conn.executemany(
            f"INSERT INTO financials_quarterly VALUES (?, ?, {', '.join('?' * len(QUARTERLY_COLUMNS))})",
            [
                (symbol, q, *(_num(v) for v in row))
                for symbol, df in results.quarterly.items()
                for q, row in zip(df.index, df[QUARTERLY_COLUMNS].itertuples(index=False))
            ],
        )
        conn.executemany(
            "INSERT INTO evaluations VALUES (?, ?, ?, ?)",
            [
                (run_id, e["symbol"], e["candidate_rank"], json.dumps(e, ensure_ascii=False, allow_nan=False))
                for e in results.evaluations
            ],
        )
        conn.executemany(
            "INSERT INTO run_failures VALUES (?, ?, ?)",
            [(run_id, symbol, reason) for symbol, reason in results.failures.items()],
        )
        # evaluations of older runs are not kept (post-mortem history is out of scope)
        conn.execute("DELETE FROM evaluations WHERE run_id < ?", (run_id,))
        conn.execute(
            "UPDATE runs SET status='succeeded', finished_at=?, price_date=?, total=?, succeeded=?, failed=? WHERE id=?",
            (
                _now().isoformat(),
                results.price_date,
                len(results.stocks),
                len(results.stocks) - len(results.failures),
                len(results.failures),
                run_id,
            ),
        )


def _num(v: object) -> float | None:
    return None if v is None or pd.isna(v) else float(v)  # type: ignore[arg-type]


def get_run(conn: sqlite3.Connection, run_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    return dict(row) if row else None


def latest_run(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def latest_successful_run(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM runs WHERE status='succeeded' ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def candidates(conn: sqlite3.Connection, run_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT result FROM evaluations WHERE run_id=? AND candidate_rank IS NOT NULL ORDER BY candidate_rank",
        (run_id,),
    )
    return [json.loads(r["result"]) for r in rows]


def evaluation(conn: sqlite3.Connection, run_id: int, symbol: str) -> dict | None:
    row = conn.execute("SELECT result FROM evaluations WHERE run_id=? AND symbol=?", (run_id, symbol)).fetchone()
    return json.loads(row["result"]) if row else None


def failures(conn: sqlite3.Connection, run_id: int) -> dict[str, str]:
    rows = conn.execute("SELECT symbol, reason FROM run_failures WHERE run_id=? ORDER BY symbol", (run_id,))
    return {r["symbol"]: r["reason"] for r in rows}


def stock(conn: sqlite3.Connection, symbol: str) -> dict | None:
    row = conn.execute("SELECT * FROM stocks WHERE symbol=?", (symbol,)).fetchone()
    return dict(row) if row else None


def search_stocks(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM stocks WHERE symbol LIKE ? ORDER BY symbol != ?, symbol LIMIT ?",
        (f"{query.upper()}%", query.upper(), limit),
    )
    return [dict(r) for r in rows]


def add_event(conn: sqlite3.Connection, symbol: str, day: date, text: str) -> int:
    with conn:
        event_id = conn.execute(
            "INSERT INTO manual_events (symbol, date, text) VALUES (?, ?, ?)", (symbol, day.isoformat(), text)
        ).lastrowid
    assert event_id is not None
    return event_id


def delete_event(conn: sqlite3.Connection, event_id: int) -> bool:
    with conn:
        return conn.execute("DELETE FROM manual_events WHERE id=?", (event_id,)).rowcount > 0


def events(conn: sqlite3.Connection, symbol: str) -> list[dict]:
    rows = conn.execute("SELECT * FROM manual_events WHERE symbol=? ORDER BY date", (symbol,))
    return [dict(r) for r in rows]


def settings(conn: sqlite3.Connection) -> dict:
    """Web-edited values keyed "section.field"; only the ones that differ from config.yaml are stored."""
    row = conn.execute("SELECT overrides FROM settings WHERE id=1").fetchone()
    return json.loads(row["overrides"]) if row else {}


def settings_updated_at(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT updated_at FROM settings WHERE id=1").fetchone()
    return row["updated_at"] if row else None


def save_settings(conn: sqlite3.Connection, values: dict, defaults: dict) -> None:
    # values equal to the default are dropped so a later change to config.yaml still reaches them
    _write_settings(conn, {k: v for k, v in values.items() if v != defaults.get(k)})


def reset_settings(conn: sqlite3.Connection) -> None:
    # still bumps updated_at: results computed with the old values are now stale too
    _write_settings(conn, {})


def _write_settings(conn: sqlite3.Connection, overrides: dict) -> None:
    with conn:
        conn.execute(
            "INSERT INTO settings (id, overrides, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET overrides=excluded.overrides, updated_at=excluded.updated_at",
            (json.dumps(overrides), _now().isoformat()),
        )


def settings_stale(conn: sqlite3.Connection) -> bool:
    """True when settings changed after the latest successful run loaded its config (at start)."""
    updated, run = settings_updated_at(conn), latest_successful_run(conn)
    if not updated or not run:
        return False
    return datetime.fromisoformat(updated) > datetime.fromisoformat(run["started_at"])


def save_investor_flow(conn: sqlite3.Connection, flow: InvestorFlow, fetched_at: datetime | None = None) -> None:
    """One row per trading day; a later fetch of the same day replaces it."""
    values = [v for t in INVESTOR_TYPES for v in (flow.buy[t], flow.sell[t])]
    with conn:
        conn.execute(
            f"INSERT OR REPLACE INTO investor_flow VALUES (?, ?, {', '.join('?' * len(FLOW_COLUMNS))}, ?)",
            (flow.date.isoformat(), flow.total_value, *values, (fetched_at or _now()).isoformat()),
        )


def investor_flow(conn: sqlite3.Connection, limit: int = 60) -> list[dict]:
    """Newest day first. `intraday` is True when the row was fetched before the market closed that day."""
    rows = conn.execute("SELECT * FROM investor_flow ORDER BY date DESC LIMIT ?", (limit,))
    out = []
    for r in rows:
        closed = datetime.combine(date.fromisoformat(r["date"]), MARKET_CLOSED_AT)
        out.append({**dict(r), "intraday": datetime.fromisoformat(r["fetched_at"]) < closed})
    return out


def save_net_flows(conn: sqlite3.Connection, flows: list[NetFlow]) -> None:
    fetched_at = _now().isoformat()
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO investor_flow_net VALUES (?, ?, ?, ?, ?)",
            [(f.date.isoformat(), f.local_institution, f.foreign, f.individual, fetched_at) for f in flows],
        )


def net_flow_history(conn: sqlite3.Connection, limit: int = 260) -> list[dict]:
    """Newest first, only days without SET buy/sell detail in investor_flow."""
    rows = conn.execute(
        "SELECT * FROM investor_flow_net WHERE date NOT IN (SELECT date FROM investor_flow) ORDER BY date DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in rows]
