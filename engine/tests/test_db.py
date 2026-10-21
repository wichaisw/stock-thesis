import sqlite3
import threading
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from shortlist import db
from shortlist.sources import QUARTERLY_COLUMNS, StockInfo
from tests.fakes import investor_flow, monthly_net

BKK = ZoneInfo("Asia/Bangkok")


def test_run_and_evaluation_round_trip(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_id = db.start_run(conn, stale_minutes=30)
    assert db.latest_run(conn)["status"] == "running"

    prices = pd.DataFrame(
        {"open": [1.0], "high": [1.2], "low": [0.9], "close": [1.1], "volume": [1000.0]},
        index=pd.DatetimeIndex(["2026-10-14"]),
    )
    quarterly = pd.DataFrame([[0.5] * len(QUARTERLY_COLUMNS)], columns=QUARTERLY_COLUMNS, index=["2026Q2"])
    ev_a = {"symbol": "AAA", "candidate_rank": 1, "cdc": {"state": "just-crossed", "eta_days": None}}
    ev_b = {"symbol": "BBB", "candidate_rank": None, "cdc": {"state": "bear-far"}}
    db.save_run(
        conn,
        run_id,
        db.RunResults(
            stocks=[StockInfo("AAA", "A Co", "Banking", "SET"), StockInfo("BBB", "B Co", "Banking", "SET"),
                    StockInfo("CCC", "C Co", "Banking", "mai")],
            prices={"AAA": prices},
            quarterly={"AAA": quarterly},
            evaluations=[ev_a, ev_b],
            failures={"CCC": "ไม่มีข้อมูลราคา"},
            price_date="2026-10-14",
        ),
    )

    run = db.latest_successful_run(conn)
    assert run["id"] == run_id and run["total"] == 3 and run["succeeded"] == 2 and run["failed"] == 1
    assert run["price_date"] == "2026-10-14"
    # evaluations without stale_price, as in runs saved before the check
    assert (run["stale_count"], run["stale_date"]) == (0, None)
    assert db.candidates(conn, run_id) == [ev_a]
    assert db.evaluation(conn, run_id, "BBB") == ev_b
    assert db.failures(conn, run_id) == {"CCC": "ไม่มีข้อมูลราคา"}
    assert conn.execute("SELECT close FROM prices_daily").fetchone()[0] == 1.1
    assert conn.execute("SELECT eps FROM financials_quarterly").fetchone()[0] == 0.5
    assert [s["symbol"] for s in db.search_stocks(conn, "b")] == ["BBB"]


def test_latest_run_counts_stale_prices_with_their_most_common_date(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_id = db.start_run(conn, stale_minutes=30)
    dates = {"AAA": "2026-10-14", "BBB": "2026-10-12", "CCC": "2026-10-12", "DDD": "2026-10-09"}
    evaluations = [
        {"symbol": s, "candidate_rank": None, "price_date": d, "stale_price": d < "2026-10-14"} for s, d in dates.items()
    ]
    db.save_run(
        conn,
        run_id,
        db.RunResults(
            stocks=[StockInfo(s, f"{s} Co", "Commerce", "SET") for s in dates],
            prices={},
            quarterly={},
            evaluations=evaluations,
            failures={},
            price_date="2026-10-14",
        ),
    )
    run = db.latest_successful_run(conn)
    assert (run["stale_count"], run["stale_date"]) == (3, "2026-10-12")


def test_connection_works_from_another_thread(tmp_path):
    # FastAPI opens a request's connection in one thread and may run the endpoint in another
    conn = db.connect(tmp_path / "t.db")
    errors = []

    def use():
        try:
            db.latest_run(conn)
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=use)
    t.start()
    t.join()
    assert errors == []


def test_settings_round_trip_drop_defaults_and_reset(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    assert db.settings(conn) == {} and db.settings_updated_at(conn) is None

    db.save_settings(conn, {"quality.min_roe": 0.08, "quality.max_de": 1.5}, {"quality.min_roe": 0.10, "quality.max_de": 1.5})
    assert db.settings(conn) == {"quality.min_roe": 0.08}
    saved_at = db.settings_updated_at(conn)

    db.reset_settings(conn)
    assert db.settings(conn) == {}
    assert db.settings_updated_at(conn) > saved_at


def test_settings_stale_compares_with_latest_successful_run_start(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "t.db")
    conn.execute("INSERT INTO runs (status, started_at) VALUES ('succeeded', '2026-10-14T17:00:00+07:00')")
    conn.commit()
    tz = datetime.fromisoformat("2026-10-14T17:00:00+07:00").tzinfo

    monkeypatch.setattr(db, "_now", lambda: datetime(2026, 10, 14, 16, 0, tzinfo=tz))
    db.save_settings(conn, {"quality.min_roe": 0.08}, {})
    assert not db.settings_stale(conn)

    # edited while that run was already going: its results used the old values
    monkeypatch.setattr(db, "_now", lambda: datetime(2026, 10, 14, 17, 1, tzinfo=tz))
    db.save_settings(conn, {"quality.min_roe": 0.07}, {})
    assert db.settings_stale(conn)

    conn.execute("INSERT INTO runs (status, started_at) VALUES ('succeeded', '2026-10-14T18:00:00+07:00')")
    conn.commit()
    assert not db.settings_stale(conn)


def test_investor_flow_same_day_keeps_latest_and_flags_intraday(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_investor_flow(conn, investor_flow(foreign_buy=40e9), datetime(2026, 10, 14, 14, 0, tzinfo=BKK))
    [row] = db.investor_flow(conn)
    assert row["intraday"] is True

    db.save_investor_flow(conn, investor_flow(foreign_buy=50e9), datetime(2026, 10, 14, 18, 30, tzinfo=BKK))
    [row] = db.investor_flow(conn)
    assert row["foreign_buy"] == 50e9 and row["intraday"] is False


def test_investor_flow_intraday_boundary_is_1700_bangkok(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_investor_flow(conn, investor_flow(date(2026, 10, 13)), datetime(2026, 10, 13, 16, 59, tzinfo=BKK))
    # same instant as 17:00 Bangkok, stored from a machine on UTC
    db.save_investor_flow(conn, investor_flow(date(2026, 10, 14)), datetime(2026, 10, 14, 10, 0, tzinfo=ZoneInfo("UTC")))
    rows = db.investor_flow(conn)
    assert [(r["date"], r["intraday"]) for r in rows] == [("2026-10-14", False), ("2026-10-13", True)]
    assert len(db.investor_flow(conn, limit=1)) == 1


def test_save_run_keeps_investor_flow_history(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_investor_flow(conn, investor_flow(date(2026, 10, 13)))
    for _ in range(2):
        run_id = db.start_run(conn, stale_minutes=30)
        db.save_run(conn, run_id, db.RunResults([], {}, {}, [], {}, None))
    assert [r["date"] for r in db.investor_flow(conn)] == ["2026-10-13"]


def test_monthly_net_refetch_replaces_the_whole_set(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_monthly_net(conn, monthly_net(("2025-09", "2025-10", "2026-09")), datetime(2026, 9, 30, 18, 0, tzinfo=BKK))
    db.save_monthly_net(conn, monthly_net(("2025-10", "2026-10"), foreign=9e9), datetime(2026, 10, 15, 18, 0, tzinfo=BKK))
    rows = db.monthly_net(conn)
    assert [(r["month"], r["foreign_net"]) for r in rows] == [("2025-10", 9e9), ("2026-10", 9e9)]
    assert {r["fetched_at"] for r in rows} == {"2026-10-15T18:00:00+07:00"}


def test_connect_drops_the_old_net_only_table(tmp_path):
    path = tmp_path / "t.db"
    sqlite3.connect(path).execute("CREATE TABLE investor_flow_net (date TEXT)").connection.commit()
    tables = {r[0] for r in db.connect(path).execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "investor_flow_net" not in tables and "investor_flow_monthly" in tables


def test_old_investor_flow_table_gets_source_set(tmp_path):
    path = tmp_path / "t.db"
    old = sqlite3.connect(path)
    cols = ", ".join(f"{c} REAL NOT NULL" for c in db.FLOW_COLUMNS)
    old.execute(f"CREATE TABLE investor_flow (date TEXT PRIMARY KEY, total_value REAL NOT NULL, {cols}, fetched_at TEXT NOT NULL)")
    old.execute(f"INSERT INTO investor_flow VALUES ('2026-10-14', 1, {', '.join('1' * len(db.FLOW_COLUMNS))}, '2026-10-14T18:00:00+07:00')")
    old.commit()
    [row] = db.investor_flow(db.connect(path))
    assert row["source"] == "set" and row["date"] == "2026-10-14"


def test_backfill_keeps_set_days_and_set_fetch_replaces_backfill(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.save_investor_flow(conn, investor_flow(date(2026, 10, 14), foreign_buy=40e9))
    days = [investor_flow(date(2026, 10, d), foreign_buy=99e9) for d in (9, 12, 14)]
    assert db.backfill_investor_flow(conn, days, "infoquest") == 2
    assert db.backfill_investor_flow(conn, days, "infoquest") == 0
    rows = {r["date"]: r for r in db.investor_flow(conn)}
    assert len(rows) == 3
    assert (rows["2026-10-14"]["source"], rows["2026-10-14"]["foreign_buy"]) == ("set", 40e9)
    assert rows["2026-10-12"]["source"] == "infoquest" and not rows["2026-10-12"]["intraday"]

    db.save_investor_flow(conn, investor_flow(date(2026, 10, 12), foreign_buy=41e9))
    row = next(r for r in db.investor_flow(conn) if r["date"] == "2026-10-12")
    assert (row["source"], row["foreign_buy"]) == ("set", 41e9)


def run_with(conn, price_date: str, candidates: list[str], others: tuple[str, ...] = ("ZZZ",)) -> int:
    """A successful run whose candidates are ranked in the given order."""
    run_id = db.start_run(conn, stale_minutes=30)
    evaluations = [{"symbol": s, "candidate_rank": i, "price": float(i)} for i, s in enumerate(candidates, start=1)]
    evaluations += [{"symbol": s, "candidate_rank": None} for s in others]
    db.save_run(conn, run_id, db.RunResults([], {}, {}, evaluations, {}, price_date))
    return run_id


def test_new_closing_date_adds_to_history(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_with(conn, "2026-10-15", ["AAA", "BBB"])
    run_with(conn, "2026-10-16", ["CCC"])
    assert db.history_dates(conn) == [{"price_date": "2026-10-16", "count": 1}, {"price_date": "2026-10-15", "count": 2}]
    old = db.history(conn, "2026-10-15")
    assert [c["symbol"] for c in old["candidates"]] == ["AAA", "BBB"]  # kept after its evaluations were deleted
    assert conn.execute("SELECT COUNT(*) FROM evaluations WHERE symbol='AAA'").fetchone()[0] == 0


def test_rerun_of_the_same_closing_date_replaces_the_whole_set(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_with(conn, "2026-10-15", ["AAA", "BBB"])
    later = run_with(conn, "2026-10-15", ["BBB"])
    h = db.history(conn, "2026-10-15")
    assert h["run_id"] == later and [c["symbol"] for c in h["candidates"]] == ["BBB"]


def test_failed_run_leaves_history_alone(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_with(conn, "2026-10-15", ["AAA"])
    db.fail_run(conn, db.start_run(conn, stale_minutes=30), "ใช้เวลาเกิน 20 นาที")
    assert db.history_dates(conn) == [{"price_date": "2026-10-15", "count": 1}]


def test_run_without_candidates_lists_its_date_with_zero(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_with(conn, "2026-10-15", ["AAA"])
    run_with(conn, "2026-10-16", [])
    assert db.history_dates(conn)[0] == {"price_date": "2026-10-16", "count": 0}
    assert db.history(conn, "2026-10-16")["candidates"] == []
    assert db.history(conn, "2026-01-01") is None


def test_first_connect_seeds_history_from_the_latest_successful_run_once(tmp_path):
    path = tmp_path / "t.db"
    conn = db.connect(path)
    run_with(conn, "2026-10-14", ["OLD"])
    run_id = run_with(conn, "2026-10-15", ["AAA", "BBB"])
    conn.executescript("DROP TABLE candidate_history; DROP TABLE candidate_history_days")  # a DB from before this change
    conn.commit()
    conn.close()
    seeded = db.connect(path)
    assert db.history_dates(seeded) == [{"price_date": "2026-10-15", "count": 2}]
    assert db.history(seeded, "2026-10-15")["run_id"] == run_id
    seeded.close()
    assert len(db.history(db.connect(path), "2026-10-15")["candidates"]) == 2  # not seeded twice


def test_holdings_add_duplicate_delete_and_survive_runs(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    assert db.add_holding(conn, "PTT", 33.5, date(2026, 10, 1))
    assert not db.add_holding(conn, "PTT", 30.0, date(2026, 10, 2))
    assert db.add_holding(conn, "CPALL", 50.0, date(2026, 9, 1))
    run_with(conn, "2026-10-20", ["PTT"])
    assert db.holdings(conn) == [
        {"symbol": "CPALL", "cost": 50.0, "buy_date": "2026-09-01"},
        {"symbol": "PTT", "cost": 33.5, "buy_date": "2026-10-01"},
    ]
    assert db.delete_holding(conn, "CPALL")
    assert not db.delete_holding(conn, "CPALL")
    assert [h["symbol"] for h in db.holdings(conn)] == ["PTT"]


def test_prices_round_trip(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    df = pd.DataFrame({"open": [1.0, 2.0], "high": [1.0, 2.0], "low": [1.0, 2.0], "close": [1.0, 2.0], "volume": [5.0, 6.0]},
                      index=pd.DatetimeIndex(["2026-10-19", "2026-10-20"]))
    db.save_run(conn, db.start_run(conn, stale_minutes=30), db.RunResults([], {"PTT": df}, {}, [], {}, "2026-10-20"))
    got = db.prices(conn, "PTT")
    assert list(got.index.strftime("%Y-%m-%d")) == ["2026-10-19", "2026-10-20"]
    assert list(got["close"]) == [1.0, 2.0]
    assert db.prices(conn, "NONE").empty
