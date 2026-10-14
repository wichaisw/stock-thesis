import pandas as pd

from shortlist import db
from shortlist.sources import QUARTERLY_COLUMNS, StockInfo


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
    assert db.candidates(conn, run_id) == [ev_a]
    assert db.evaluation(conn, run_id, "BBB") == ev_b
    assert db.failures(conn, run_id) == {"CCC": "ไม่มีข้อมูลราคา"}
    assert conn.execute("SELECT close FROM prices_daily").fetchone()[0] == 1.1
    assert conn.execute("SELECT eps FROM financials_quarterly").fetchone()[0] == 0.5
    assert [s["symbol"] for s in db.search_stocks(conn, "b")] == ["BBB"]
