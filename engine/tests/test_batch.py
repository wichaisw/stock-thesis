import re
from datetime import date, datetime, timedelta

import pytest

from shortlist import batch, db
from shortlist.config import load_config
from shortlist.sources import StockInfo
from tests.fakes import FakeFinancials, FakePrices, healthy_quarters, market_caps, price_history

CFG = load_config()


def fake_sources():
    stocks = [StockInfo(s, f"{s} Co", "Commerce", "SET") for s in ["AAA", "BBB", "CCC", "DDD"]]
    # CCC has no prices, BBB's statements fail
    # AAA needs market caps and dividends from the price source for its fair value panel
    prices = FakePrices(
        {"AAA": price_history(), "BBB": price_history(), "DDD": price_history()},
        {"AAA": market_caps(healthy_quarters())},
    )
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


DNS = "An error occurred while fetching stock list: [Errno 8] nodename nor servname provided, or not known"
NOT_FOUND = "Stock with symbol FLE not found."
TODAY = date(2026, 10, 14)


def many(n: int) -> list[StockInfo]:
    return [StockInfo(f"S{i:02d}", f"S{i:02d} Co", "Commerce", "SET") for i in range(n)]


def outage_sources(errors: dict[str, str], n: int = 10):
    stocks = many(n)
    syms = [s.symbol for s in stocks]
    prices = FakePrices({s: price_history() for s in syms}, {s: market_caps(healthy_quarters()) for s in syms})
    return prices, FakeFinancials(stocks, {s: healthy_quarters() for s in syms}, errors=errors)


@pytest.mark.parametrize(
    "message",
    [
        DNS,
        "Failed to perform, curl: (6) Could not resolve host: query2.finance.yahoo.com.",
        "curl: (28) Operation timed out after 10001 milliseconds",
        "ConnectError: [Errno 61] Connection refused",
    ],
)
def test_network_errors_are_recognised(message):
    assert batch.is_network_error(message)


@pytest.mark.parametrize("message", [NOT_FOUND, "Finnomena API error", "ไม่มีข้อมูลราคา"])
def test_other_errors_are_not_network_errors(message):
    assert not batch.is_network_error(message)


def test_network_outage_stops_the_batch_and_keeps_the_last_good_run(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    good = batch.run(conn, *fake_sources(), CFG, today=TODAY)

    prices, fin = outage_sources({f"S{i:02d}": DNS for i in range(5)})
    with pytest.raises(batch.BatchAborted):
        batch.run(conn, prices, fin, CFG, today=TODAY)

    run = db.latest_run(conn)
    assert run["status"] == "failed"
    assert run["error"].startswith("เครือข่ายใช้ไม่ได้")  # no class name in front, the UI shows it as is
    assert "S04" in run["error"] and "Errno 8" in run["error"]
    assert fin.calls == ["S00", "S01", "S02", "S03", "S04"]  # the rest are never fetched
    assert db.latest_successful_run(conn)["id"] == good


def test_network_errors_broken_by_another_error_do_not_stop_the_batch(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    errors = {f"S{i:02d}": DNS for i in [0, 1, 2, 3, 5, 6, 7, 8]} | {"S04": NOT_FOUND}
    run_id = batch.run(conn, *outage_sources(errors), CFG, today=TODAY)

    run = db.get_run(conn, run_id)
    assert run["status"] == "succeeded"
    assert (run["succeeded"], run["failed"]) == (1, 9)


def test_price_outage_stops_the_batch_before_statements(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    stocks = many(8)
    prices = FakePrices({}, unreachable="เชื่อมต่อแหล่งราคาไม่ได้: [Errno 8] nodename nor servname provided")
    fin = FakeFinancials(stocks, {})
    with pytest.raises(batch.BatchAborted):
        batch.run(conn, prices, fin, CFG, today=TODAY)

    run = db.latest_run(conn)
    assert run["status"] == "failed" and run["error"].startswith("เครือข่ายใช้ไม่ได้")
    assert "เชื่อมต่อแหล่งราคาไม่ได้" in run["error"]
    assert fin.calls == []


def test_missing_prices_with_network_up_keep_the_old_reason(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    stocks = many(10)
    prices = FakePrices({"S09": price_history()}, {"S09": market_caps(healthy_quarters())})
    run_id = batch.run(conn, prices, FakeFinancials(stocks, {"S09": healthy_quarters()}), CFG, today=TODAY)

    assert db.get_run(conn, run_id)["status"] == "succeeded"
    fails = db.failures(conn, run_id)
    assert len(fails) == 9 and set(fails.values()) == {"ไม่มีข้อมูลราคา"}


def test_empty_market_caps_during_an_outage_fail_the_stock(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    stocks = many(3)
    syms = [s.symbol for s in stocks]
    down = "เชื่อมต่อแหล่งราคาไม่ได้: [Errno 8] nodename nor servname provided"
    # prices came through, then the network dropped before the market cap history
    prices = FakePrices({s: price_history() for s in syms}, {"S00": market_caps(healthy_quarters())}, unreachable=down)
    run_id = batch.run(conn, prices, FakeFinancials(stocks, {s: healthy_quarters() for s in syms}), CFG, today=TODAY)

    fails = db.failures(conn, run_id)
    assert set(fails) == {"S01", "S02"}
    assert all(r.startswith("ดึง market cap ไม่ได้: เชื่อมต่อแหล่งราคาไม่ได้") for r in fails.values())
    assert db.evaluation(conn, run_id, "S00") is not None


def test_five_empty_market_caps_during_an_outage_stop_the_batch(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    stocks = many(8)
    syms = [s.symbol for s in stocks]
    prices = FakePrices({s: price_history() for s in syms}, unreachable="เชื่อมต่อแหล่งราคาไม่ได้: timed out")
    fin = FakeFinancials(stocks, {s: healthy_quarters() for s in syms})
    with pytest.raises(batch.BatchAborted):
        batch.run(conn, prices, fin, CFG, today=TODAY)
    assert len(fin.calls) == 5


def test_empty_market_caps_with_network_up_are_still_evaluated(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    run_id = batch.run(conn, *fake_sources(), CFG, today=TODAY)
    # DDD has no market cap history in the fakes, and the fake source is reachable
    ev = db.evaluation(conn, run_id, "DDD")
    assert ev is not None
    assert all(i["fair_value"] is None for i in ev["fair_value"]["items"] if i["method"] != "peer_pe")


def test_run_over_the_time_limit_stops(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "t.db")
    prices, fin = outage_sources({})
    # time jumps past 20 minutes once two stocks' statements are in
    monkeypatch.setattr(batch.time, "monotonic", lambda: 21 * 60.0 if len(fin.calls) >= 2 else 0.0)
    with pytest.raises(batch.BatchAborted):
        batch.run(conn, prices, fin, CFG, today=TODAY)

    run = db.latest_run(conn)
    assert run["status"] == "failed"
    assert "20 นาที" in run["error"] and "ดึงงบ" in run["error"]
    assert fin.calls == ["S00", "S01"]


def test_log_has_the_duration_of_every_phase(tmp_path):
    lines: list[str] = []
    batch.run(db.connect(tmp_path / "t.db"), *fake_sources(), CFG, today=TODAY, log=lines.append)
    for phase in ["รายชื่อหุ้น", "ได้ราคา", "ดึงงบและ market cap", "ประเมิน", "รวม"]:
        line = next((ln for ln in lines if phase in ln), None)
        assert line is not None and re.search(r"\d+ วินาที", line), (phase, lines)


def test_abort_reason_is_logged(tmp_path):
    lines: list[str] = []
    with pytest.raises(batch.BatchAborted):
        batch.run(db.connect(tmp_path / "t.db"), *outage_sources({f"S{i:02d}": DNS for i in range(5)}), CFG,
                  today=TODAY, log=lines.append)
    assert lines[-1].startswith("เครือข่ายใช้ไม่ได้")


def test_network_error_on_the_stock_list_stops_with_a_readable_reason(tmp_path):
    conn = db.connect(tmp_path / "t.db")

    class Down:
        def list_stocks(self):
            raise ValueError("An error occurred while requesting securities data: [Errno 61] Connection refused")

    with pytest.raises(batch.BatchAborted):
        batch.run(conn, FakePrices({}), Down(), CFG)
    run = db.latest_run(conn)
    assert run["status"] == "failed"
    assert run["error"].startswith("เครือข่ายใช้ไม่ได้: ดึงรายชื่อหุ้นไม่ได้: ")
    assert "Connection refused" in run["error"]
