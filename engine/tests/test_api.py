from datetime import date

import pytest
from fastapi.testclient import TestClient

from shortlist import db
from shortlist.api import create_app
from shortlist.sources import StockInfo
from tests.fakes import FakeFinancials, FakePrices, healthy_quarters, price_history

TODAY = date(2026, 10, 14)


def fake_sources(_cfg):
    stocks = [StockInfo("AAA", "A Co", "Tourism & Leisure", "SET"), StockInfo("BBB", "B Co", "Commerce", "SET")]
    prices = FakePrices({"AAA": price_history(120, 14, 11)})
    return prices, FakeFinancials(stocks, {"AAA": healthy_quarters()})


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=tmp_path / "t.db", sources=fake_sources, today=lambda: TODAY)
    return TestClient(app), tmp_path / "t.db"


def test_no_successful_run_yet(client):
    c, _ = client
    assert c.get("/runs/latest").json() == {"latest": None, "latest_succeeded": None}
    assert c.get("/candidates").json() == {"run": None, "candidates": [], "failure_count": 0}
    assert c.get("/failures").json() == {"run": None, "failures": []}
    assert c.get("/stocks/AAA").status_code == 404


def test_run_then_read_results(client):
    c, _ = client
    r = c.post("/runs")
    assert r.status_code == 202
    run = c.get(f"/runs/{r.json()['run']['id']}").json()
    assert run["status"] == "succeeded"

    body = c.get("/candidates").json()
    assert body["run"]["id"] == run["id"]
    assert body["failure_count"] == 1
    assert c.get("/failures").json()["failures"] == [
        {"symbol": "BBB", "name": "B Co", "reason": "ไม่มีข้อมูลราคา"}
    ]

    detail = c.get("/stocks/aaa").json()
    assert detail["evaluation"]["symbol"] == "AAA"
    assert detail["failure"] is None
    assert detail["hints"]["sector_matched"]
    assert any(e["kind"] == "statement" for e in detail["events"])

    failed = c.get("/stocks/BBB").json()
    assert failed["evaluation"] is None and failed["failure"] == "ไม่มีข้อมูลราคา"

    found = {s["symbol"]: s["failure"] for s in c.get("/stocks/search", params={"q": "b"}).json()}
    assert found == {"BBB": "ไม่มีข้อมูลราคา"}


def test_run_refused_while_running(client):
    c, path = client
    db.start_run(db.connect(path), stale_minutes=30)
    r = c.post("/runs")
    assert r.status_code == 409
    assert "กำลังรัน" in r.json()["detail"]


def test_manual_events_survive_new_run_and_hide_past(client):
    c, _ = client
    c.post("/runs")
    future = c.post("/stocks/AAA/events", json={"date": "2026-12-14", "text": "XD 0.50 บาท"}).json()
    c.post("/stocks/AAA/events", json={"date": "2026-10-01", "text": "ผ่านไปแล้ว"})
    c.post("/runs")

    manual = [e for e in c.get("/stocks/AAA").json()["events"] if e["kind"] == "manual"]
    assert [e["label"] for e in manual] == ["XD 0.50 บาท"]

    assert c.delete(f"/events/{future['id']}").status_code == 204
    assert not [e for e in c.get("/stocks/AAA").json()["events"] if e["kind"] == "manual"]
    assert c.delete(f"/events/{future['id']}").status_code == 404


def test_broken_sources_mark_run_failed(tmp_path):
    def broken(_cfg):
        raise RuntimeError("no network")

    c = TestClient(create_app(db_path=tmp_path / "t.db", sources=broken, today=lambda: TODAY))
    run_id = c.post("/runs").json()["run"]["id"]
    run = c.get(f"/runs/{run_id}").json()
    assert run["status"] == "failed" and "no network" in run["error"]


def test_event_needs_text(client):
    c, _ = client
    c.post("/runs")
    assert c.post("/stocks/AAA/events", json={"date": "2026-12-14", "text": ""}).status_code == 422



def test_schema_exists_before_first_request(tmp_path):
    # parallel first requests racing to create the schema can hit "database is locked"
    import sqlite3

    create_app(db_path=tmp_path / "fresh.db", sources=fake_sources, today=lambda: TODAY)
    tables = {r[0] for r in sqlite3.connect(tmp_path / "fresh.db").execute("SELECT name FROM sqlite_master")}
    assert {"runs", "evaluations"} <= tables
