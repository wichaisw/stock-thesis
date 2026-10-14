from datetime import date, datetime, timedelta

import pytest

from shortlist import batch, db
from shortlist.config import load_config
from shortlist.sources import StockInfo
from tests.fakes import FakeFinancials, FakePrices, healthy_quarters, price_history

CFG = load_config()


def fake_sources():
    stocks = [StockInfo(s, f"{s} Co", "Commerce", "SET") for s in ["AAA", "BBB", "CCC", "DDD"]]
    # CCC has no prices, BBB's statements fail
    prices = FakePrices({"AAA": price_history(), "BBB": price_history(), "DDD": price_history()})
    fin = FakeFinancials(stocks, {"AAA": healthy_quarters(), "DDD": healthy_quarters()}, broken={"BBB"})
    return prices, fin


def test_one_stock_failing_does_not_stop_the_batch(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_id = batch.run(conn, *fake_sources(), CFG, today=date(2026, 10, 14))

    run = db.get_run(conn, run_id)
    assert run["status"] == "succeeded"
    assert (run["total"], run["succeeded"], run["failed"]) == (4, 2, 2)
    fails = db.failures(conn, run_id)
    assert fails["CCC"] == "ไม่มีข้อมูลราคา"
    assert "Finnomena API error" in fails["BBB"]

    ev = db.evaluation(conn, run_id, "AAA")
    assert ev["quality"]["passed"]
    assert ev["fair_value"]["summary"]["computed"] > 0
    assert ev["cdc"]["state"] == "bull"
    assert ev["risk_reward"]["hold_months"] == 1.02  # 31 days to the Q3 deadline
    assert db.evaluation(conn, run_id, "BBB") is None


def test_second_run_is_refused_while_first_is_running(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    first = db.start_run(conn, stale_minutes=30)
    with pytest.raises(db.RunInProgress):
        batch.run(conn, *fake_sources(), CFG)
    assert db.get_run(conn, first)["status"] == "running"
    assert db.latest_run(conn)["id"] == first


def test_stale_running_run_is_marked_failed(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    now = datetime.now().astimezone()
    stale = db.start_run(conn, stale_minutes=30, now=now - timedelta(minutes=31))
    second = db.start_run(conn, stale_minutes=30, now=now)
    assert db.get_run(conn, stale)["status"] == "failed"
    assert db.get_run(conn, second)["status"] == "running"


def test_crash_marks_run_failed(tmp_path):
    conn = db.connect(tmp_path / "t.db")

    class Broken:
        def list_stocks(self):
            raise ConnectionError("github down")

    with pytest.raises(ConnectionError):
        batch.run(conn, FakePrices({}), Broken(), CFG)
    run = db.latest_run(conn)
    assert run["status"] == "failed" and "github down" in run["error"]
