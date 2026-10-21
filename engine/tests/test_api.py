from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from shortlist import db
from shortlist.api import create_app
from shortlist.sources import StockInfo
from tests.fakes import FakeFinancials, FakeInvestorFlow, FakePrices, healthy_quarters, investor_flow, monthly_net, price_history

TODAY = date(2026, 10, 14)


def fake_sources(_cfg):
    stocks = [StockInfo("AAA", "A Co", "Tourism & Leisure", "SET"), StockInfo("BBB", "B Co", "Commerce", "SET")]
    prices = FakePrices({"AAA": price_history(120, 14, 11)})
    return prices, FakeFinancials(stocks, {"AAA": healthy_quarters()}), FakeInvestorFlow()


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=tmp_path / "t.db", sources=fake_sources, today=lambda: TODAY)
    return TestClient(app), tmp_path / "t.db"


def test_no_successful_run_yet(client):
    c, _ = client
    assert c.get("/runs/latest").json() == {"latest": None, "latest_succeeded": None}
    assert c.get("/candidates").json() == {"run": None, "candidates": [], "failure_count": 0, "stale": False}
    assert c.get("/failures").json() == {"run": None, "failures": []}
    assert c.get("/stocks/AAA").status_code == 404


def test_candidate_history_follows_the_run(client):
    c, _ = client
    assert c.get("/candidates/history").json() == []
    run_id = c.post("/runs").json()["run"]["id"]
    body = c.get("/candidates").json()
    day = body["run"]["price_date"]
    assert c.get("/candidates/history").json() == [{"price_date": day, "count": len(body["candidates"])}]
    h = c.get(f"/candidates/history/{day}").json()
    assert h["candidates"] == body["candidates"] and h["price_date"] == day
    assert h["run_id"] == run_id
    assert c.get("/candidates/history/2000-01-01").status_code == 404


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


def field(body: dict, key: str) -> dict:
    return next(f for f in body["fields"] if f["key"] == key)


def test_settings_start_at_defaults(client):
    c, _ = client
    body = c.get("/settings").json()
    liq = field(body, "liquidity.min_avg_traded_value")
    assert liq["value"] == liq["default"] == 10_000_000 and liq["unit"] == "million_baht"
    assert not any(f["key"].startswith("cdc.fast") for f in body["fields"])
    assert body["stale"] is False and body["updated_at"] is None


def test_gate_methods_are_marked_in_the_fair_value_options(client):
    c, _ = client
    options = {o["value"]: o["label"] for o in field(c.get("/settings").json(), "fair_value.enabled")["options"]}
    assert options["peer_pe"].endswith("· gate method") and options["justified_pbv"].endswith("· gate method")
    assert "gate" not in options["pbv_median"]
    assert field(c.get("/settings").json(), "candidates.min_gate_mos")["value"] == 0.10


def test_negative_value_is_rejected_on_its_field(client):
    c, _ = client
    r = c.put("/settings", json={"quality.max_de": -1})
    assert r.status_code == 422
    assert r.json()["detail"]["errors"] == {"quality.max_de": "ค่าต้องไม่ติดลบ"}
    assert c.get("/settings").json()["updated_at"] is None


def test_conflicting_fields_are_rejected(client):
    c, _ = client
    r = c.put("/settings", json={"quality.ocf_window": 4, "quality.ocf_min_positive": 5})
    assert r.status_code == 422
    assert "ไม่เกินจำนวนไตรมาสที่ดู OCF" in r.json()["detail"]["errors"]["quality.ocf_min_positive"]


def test_one_bad_value_saves_nothing(client):
    c, _ = client
    c.put("/settings", json={"liquidity.min_avg_traded_value": 5_000_000})
    r = c.put("/settings", json={"liquidity.min_avg_traded_value": 3_000_000, "quality.min_roe": -0.1})
    assert r.status_code == 422 and set(r.json()["detail"]["errors"]) == {"quality.min_roe"}
    body = c.get("/settings").json()
    assert field(body, "liquidity.min_avg_traded_value")["value"] == 5_000_000
    assert field(body, "quality.min_roe")["value"] == 0.10


def test_locked_key_is_rejected(client):
    c, _ = client
    r = c.put("/settings", json={"cdc.fast_length": 5})
    assert r.status_code == 422 and "cdc.fast_length" in r.json()["detail"]["errors"]


def test_disabling_both_gate_methods_is_rejected_on_the_fair_value_field(client):
    c, _ = client
    before = field(c.get("/settings").json(), "fair_value.enabled")["value"]
    r = c.put("/settings", json={"fair_value.enabled": ["pe_median", "pbv_median"]})
    assert r.status_code == 422
    assert set(r.json()["detail"]["errors"]) == {"fair_value.enabled"}
    assert "gate" in r.json()["detail"]["errors"]["fair_value.enabled"]
    assert field(c.get("/settings").json(), "fair_value.enabled")["value"] == before


def test_empty_state_list_is_rejected(client):
    c, _ = client
    r = c.put("/settings", json={"candidates.accepted_states": []})
    assert r.json()["detail"]["errors"] == {"candidates.accepted_states": "ต้องเลือกอย่างน้อยหนึ่งตัวเลือก"}


def test_reset_after_editing_several_fields(client):
    c, _ = client
    c.put("/settings", json={"quality.min_roe": 0.08, "quality.max_de": 2, "fair_value.enabled": ["pe_median"]})
    body = c.delete("/settings").json()
    assert all(f["value"] == f["default"] for f in body["fields"])
    assert body["updated_at"] is not None


def test_untouched_field_follows_new_yaml_default(tmp_path):
    import yaml

    from shortlist.config import DEFAULT_PATH

    path = tmp_path / "config.yaml"
    raw = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    c = TestClient(create_app(db_path=tmp_path / "t.db", config_path=path, sources=fake_sources, today=lambda: TODAY))
    c.put("/settings", json={"quality.max_de": 2})

    raw["quality"]["min_roe"] = 0.12
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    assert field(c.get("/settings").json(), "quality.min_roe")["value"] == 0.12


def test_values_equal_to_default_are_not_stored(client):
    c, path = client
    c.put("/settings", json={"quality.min_roe": 0.1, "quality.max_de": 2})
    assert db.settings(db.connect(path)) == {"quality.max_de": 2.0}


def test_saved_settings_reach_the_next_run(client):
    c, _ = client
    c.post("/runs")
    assert c.get("/stocks/AAA").json()["evaluation"]["liquidity"]["passed"]

    c.put("/settings", json={"liquidity.min_avg_traded_value": 1_000_000_000})
    assert c.get("/candidates").json()["stale"] is True

    c.post("/runs")
    assert not c.get("/stocks/AAA").json()["evaluation"]["liquidity"]["passed"]
    assert c.get("/candidates").json()["stale"] is False


def test_web_started_batch_logs_the_funnel(client, caplog):
    c, _ = client
    with caplog.at_level("INFO", logger="shortlist"):
        c.post("/runs")
    assert "ผ่าน liquidity" in caplog.text and "candidates" in caplog.text


def test_manual_investor_flow_fetch_saves_or_reports_why(tmp_path):
    flow_src = FakeInvestorFlow()

    def sources(_cfg):
        return *fake_sources(_cfg)[:2], flow_src

    c = TestClient(create_app(db_path=tmp_path / "t.db", sources=sources, today=lambda: TODAY))
    res = c.post("/investor-flow")
    assert res.status_code == 200 and res.json()["date"] == "2026-10-14"

    flow_src.error = ConnectionError("Incapsula blocked")
    res = c.post("/investor-flow")
    assert res.status_code == 502 and "Incapsula blocked" in res.json()["detail"]
    assert [r["foreign_buy"] for r in c.get("/investor-flow").json()] == [50e9]


def test_investor_flow_newest_first_with_limit_and_intraday(client):
    c, path = client
    assert c.get("/investor-flow").json() == []
    conn = db.connect(path)
    bkk = ZoneInfo("Asia/Bangkok")
    db.save_investor_flow(conn, investor_flow(date(2026, 10, 13)), datetime(2026, 10, 13, 18, 30, tzinfo=bkk))
    db.save_investor_flow(conn, investor_flow(date(2026, 10, 14)), datetime(2026, 10, 14, 14, 0, tzinfo=bkk))

    rows = c.get("/investor-flow").json()
    assert [(r["date"], r["intraday"]) for r in rows] == [("2026-10-14", True), ("2026-10-13", False)]
    assert rows[0]["foreign_buy"] == 50e9 and "total_value" in rows[0] and "fetched_at" in rows[0]
    assert rows[0]["source"] == "set"
    assert [r["date"] for r in c.get("/investor-flow?limit=1").json()] == ["2026-10-14"]
    assert c.get("/investor-flow?limit=0").status_code == 422


def test_investor_flow_monthly_oldest_first_or_empty(client):
    c, path = client
    assert c.get("/investor-flow/monthly").json() == []
    db.save_monthly_net(db.connect(path), monthly_net(("2025-10", "2025-11", "2026-10")))
    rows = c.get("/investor-flow/monthly").json()
    assert [r["month"] for r in rows] == ["2025-10", "2025-11", "2026-10"]
    assert rows[0]["foreign_net"] == 5e9 and "fetched_at" in rows[0]


def test_holdings_add_validate_verdict_and_delete(client):
    c, _ = client
    c.post("/runs")
    # added after the run: the verdict comes straight from the latest run, no new batch needed
    assert c.post("/holdings", json={"symbol": "bbb", "cost": 5.0, "buy_date": "2026-08-03"}).status_code == 201
    assert c.post("/holdings", json={"symbol": "AAA", "cost": 12.0, "buy_date": "2026-08-03"}).status_code == 201

    bad = [
        ({"symbol": "ZZZ", "cost": 1.0, "buy_date": "2026-08-03"}, 404, "ไม่พบหุ้น ZZZ"),
        ({"symbol": "AAA", "cost": 1.0, "buy_date": "2026-08-03"}, 409, "ถือ AAA อยู่แล้ว"),
        ({"symbol": "BBB", "cost": 0, "buy_date": "2026-08-03"}, 422, "ราคาต้นทุนต้องมากกว่า 0"),
        ({"symbol": "BBB", "cost": 1.0, "buy_date": "2026-10-15"}, 422, "วันที่ซื้อต้องไม่เกินวันนี้"),
    ]
    for body, status, message in bad:
        r = c.post("/holdings", json=body)
        assert r.status_code == status and r.json()["detail"].startswith(message)

    body = c.get("/holdings").json()
    assert body["price_date"] == "2026-10-14"
    aaa, bbb = body["holdings"]  # no_data sorts last
    assert aaa["symbol"] == "AAA" and aaa["verdict"] in ["cut", "prepare", "wait", "hold"]
    assert aaa["price"] == 11.0 and aaa["stop"] is not None and aaa["pnl"] < 0
    assert (bbb["symbol"], bbb["verdict"], bbb["reasons"]) == ("BBB", "no_data", ["ไม่มีข้อมูลราคา"])

    assert c.delete("/holdings/bbb").status_code == 204
    assert c.delete("/holdings/BBB").status_code == 404
    assert [h["symbol"] for h in c.get("/holdings").json()["holdings"]] == ["AAA"]


def test_holdings_sort_cut_first(client):
    c, path = client
    c.post("/runs")
    conn = db.connect(path)
    # AAA slid from 14 to 11: the close is under the stop frozen at the buy date (about 11.9)
    db.add_holding(conn, "AAA", 12.5, date(2026, 8, 5))
    rows = c.get("/holdings").json()["holdings"]
    assert rows[0]["verdict"] == "cut"
    assert any("ต่ำกว่า stop" in r for r in rows[0]["reasons"])
