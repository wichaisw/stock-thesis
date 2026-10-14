import logging
import os
import sqlite3
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

from typing import Any, get_args

from fastapi import BackgroundTasks, Body, Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, ValidationError

from shortlist import batch, db
from shortlist.config import DEFAULT_PATH as CONFIG_PATH
from shortlist.config import SECTION_TITLES, STATE_LABELS, Config, editable_fields, load_config
from shortlist.core import catalyst
from shortlist.core.fair_value import LABELS as FAIR_VALUE_LABELS

log = logging.getLogger("shortlist")
# uvicorn only configures its own loggers; without this the batch funnel (INFO) is dropped
if not log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s:     %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)


class EventIn(BaseModel):
    date: date
    text: str = Field(min_length=1, max_length=200)


OPTION_LABELS = FAIR_VALUE_LABELS | STATE_LABELS


def _limits(field) -> dict:
    out = {}
    for m in field.metadata:
        for attr, key in (("ge", "min"), ("gt", "min"), ("le", "max"), ("lt", "max")):
            if getattr(m, attr, None) is not None:
                out[key] = getattr(m, attr)
    return out


def settings_fields(cfg: Config, defaults: Config) -> list[dict]:
    """Flat list the settings form renders; all metadata comes from the Field() in config.py."""
    fields = []
    for section, name, field in editable_fields():
        extra = field.json_schema_extra
        assert isinstance(extra, dict)
        item = {
            "key": f"{section}.{name}",
            "section": section,
            "section_title": SECTION_TITLES[section],
            "title": field.title,
            "description": field.description,
            "unit": extra["unit"],
            "value": getattr(getattr(cfg, section), name),
            "default": getattr(getattr(defaults, section), name),
        } | _limits(field)
        if extra["unit"] == "choice":
            (literal,) = get_args(field.annotation)
            item |= {"type": "choice", "options": [{"value": v, "label": OPTION_LABELS[v]} for v in get_args(literal)]}
        else:
            item["type"] = "int" if field.annotation is int else "float"
        fields.append(item)
    return fields


def _show(value: Any, unit: str) -> str:
    # limits are stored in engine units but the form shows percent and million baht
    if unit == "percent":
        return f"{value * 100:g}%"
    if unit == "million_baht":
        return f"{value / 1e6:g} ล้านบาท"
    return f"{value:g}"


def thai_error(err: dict, unit: str) -> str:
    ctx = err.get("ctx", {})
    match err["type"]:
        case "greater_than_equal" if ctx["ge"] == 0:
            return "ค่าต้องไม่ติดลบ"
        case "greater_than_equal":
            return f"ต้องไม่น้อยกว่า {_show(ctx['ge'], unit)}"
        case "greater_than":
            return f"ต้องมากกว่า {_show(ctx['gt'], unit)}"
        case "less_than_equal":
            return f"ต้องไม่เกิน {_show(ctx['le'], unit)}"
        case "less_than":
            return f"ต้องน้อยกว่า {_show(ctx['lt'], unit)}"
        case "int_parsing" | "int_from_float" | "int_type":
            return "ต้องเป็นจำนวนเต็ม"
        case "float_parsing" | "float_type":
            return "ต้องเป็นตัวเลข"
        case "too_short":
            return "ต้องเลือกอย่างน้อยหนึ่งตัวเลือก"
        case "literal_error":
            return "มีตัวเลือกที่ไม่รู้จัก"
        case "value_error":
            return str(ctx.get("error", err["msg"]))
        case _:
            return err["msg"]


def create_app(
    db_path: Path | str = db.DEFAULT_PATH,
    config_path: Path = CONFIG_PATH,
    sources: Callable[[Config], tuple] = batch.default_sources,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    app = FastAPI(title="shortlist engine")
    # create the schema up front: parallel first requests racing to create it (and to switch
    # the file to WAL) get "database is locked"
    db.connect(db_path).close()

    def conn() -> Iterator[sqlite3.Connection]:
        c = db.connect(db_path)
        try:
            yield c
        finally:
            c.close()

    def current_config(c: sqlite3.Connection) -> Config:
        return load_config(config_path, db.settings(c))

    def run_in_background(run_id: int) -> None:
        c = db.connect(db_path)
        try:
            try:
                cfg = current_config(c)
                prices, financials, flow = sources(cfg)
            except Exception as e:
                db.fail_run(c, run_id, f"{type(e).__name__}: {e}")
                raise
            batch.execute(c, run_id, prices, financials, cfg, log=log.info, flow_src=flow)
        except Exception:
            # the run is already marked failed; keep the server alive
            log.exception("batch run %s failed", run_id)
        finally:
            c.close()

    def settings_payload(c: sqlite3.Connection) -> dict:
        return {
            "fields": settings_fields(current_config(c), load_config(config_path)),
            "updated_at": db.settings_updated_at(c),
            "stale": db.settings_stale(c),
        }

    @app.get("/settings")
    def get_settings(c: sqlite3.Connection = Depends(conn)) -> dict:
        return settings_payload(c)

    @app.put("/settings")
    def put_settings(values: dict[str, Any] = Body(...), c: sqlite3.Connection = Depends(conn)) -> dict:
        units = {f"{s}.{n}": f.json_schema_extra["unit"] for s, n, f in editable_fields()}  # type: ignore[index]
        locked = {k: "ช่องนี้แก้บนเว็บไม่ได้" for k in values if k not in units}
        if locked:
            raise HTTPException(422, {"errors": locked})
        try:
            cfg = load_config(config_path, values)
        except ValidationError as e:
            errors: dict[str, str] = {}
            for err in e.errors():
                key = ".".join(map(str, err["loc"][:2]))
                errors.setdefault(key, thai_error(err, units.get(key, "")))
            raise HTTPException(422, {"errors": errors})
        defaults = load_config(config_path)
        # store the validated values so "8" and 8.0 compare equal to the default
        db.save_settings(
            c,
            {k: getattr(getattr(cfg, k.split(".")[0]), k.split(".")[1]) for k in values},
            {k: getattr(getattr(defaults, k.split(".")[0]), k.split(".")[1]) for k in values},
        )
        return settings_payload(c)

    @app.delete("/settings")
    def delete_settings(c: sqlite3.Connection = Depends(conn)) -> dict:
        db.reset_settings(c)
        return settings_payload(c)

    @app.get("/runs/latest")
    def latest_runs(c: sqlite3.Connection = Depends(conn)) -> dict:
        return {"latest": db.latest_run(c), "latest_succeeded": db.latest_successful_run(c)}

    @app.post("/runs", status_code=202)
    def start_run(tasks: BackgroundTasks, c: sqlite3.Connection = Depends(conn)) -> dict:
        cfg = current_config(c)
        try:
            run_id = db.start_run(c, cfg.batch.stale_run_minutes)
        except db.RunInProgress as e:
            raise HTTPException(409, str(e))
        tasks.add_task(run_in_background, run_id)
        return {"run": db.get_run(c, run_id)}

    @app.get("/runs/{run_id}")
    def get_run(run_id: int, c: sqlite3.Connection = Depends(conn)) -> dict:
        run = db.get_run(c, run_id)
        if not run:
            raise HTTPException(404, "ไม่พบ run")
        return run

    @app.get("/candidates")
    def candidates(c: sqlite3.Connection = Depends(conn)) -> dict:
        run = db.latest_successful_run(c)
        stale = db.settings_stale(c)
        if not run:
            return {"run": None, "candidates": [], "failure_count": 0, "stale": stale}
        return {"run": run, "candidates": db.candidates(c, run["id"]), "failure_count": run["failed"], "stale": stale}

    @app.get("/failures")
    def failures(c: sqlite3.Connection = Depends(conn)) -> dict:
        run = db.latest_successful_run(c)
        if not run:
            return {"run": None, "failures": []}
        return {
            "run": run,
            "failures": [
                {"symbol": s, "name": (db.stock(c, s) or {}).get("name"), "reason": r}
                for s, r in db.failures(c, run["id"]).items()
            ],
        }

    @app.get("/investor-flow")
    def investor_flow(limit: int = Query(60, ge=1), c: sqlite3.Connection = Depends(conn)) -> list[dict]:
        return db.investor_flow(c, limit)

    @app.get("/investor-flow/history")
    def investor_flow_history(limit: int = Query(260, ge=1), c: sqlite3.Connection = Depends(conn)) -> list[dict]:
        return db.net_flow_history(c, limit)

    @app.post("/investor-flow")
    def fetch_investor_flow(c: sqlite3.Connection = Depends(conn)) -> dict:
        # waits for the result: one page load takes a few seconds, unlike a whole batch
        error = batch.record_investor_flow(c, sources(current_config(c))[2], log.info)
        if error:
            raise HTTPException(502, error)
        return db.investor_flow(c, 1)[0]

    @app.get("/stocks/search")
    def search(q: str, c: sqlite3.Connection = Depends(conn)) -> list[dict]:
        run = db.latest_successful_run(c)
        fails = db.failures(c, run["id"]) if run else {}
        return [s | {"failure": fails.get(s["symbol"])} for s in db.search_stocks(c, q.strip())]

    @app.get("/stocks/{symbol}")
    def stock_detail(symbol: str, c: sqlite3.Connection = Depends(conn)) -> dict:
        symbol = symbol.upper()
        info = db.stock(c, symbol)
        if not info:
            raise HTTPException(404, "ไม่พบหุ้น")
        run = db.latest_successful_run(c)
        cfg = current_config(c)
        return {
            "stock": info,
            "run": run,
            "evaluation": db.evaluation(c, run["id"], symbol) if run else None,
            "failure": db.failures(c, run["id"]).get(symbol) if run else None,
            "hints": catalyst.hints(info["sector"], cfg.catalyst),
            "events": catalyst.event_calendar(today(), cfg.catalyst, db.events(c, symbol)),
        }

    @app.post("/stocks/{symbol}/events", status_code=201)
    def add_event(symbol: str, event: EventIn, c: sqlite3.Connection = Depends(conn)) -> dict:
        symbol = symbol.upper()
        if not db.stock(c, symbol):
            raise HTTPException(404, "ไม่พบหุ้น")
        event_id = db.add_event(c, symbol, event.date, event.text.strip())
        return {"id": event_id, "symbol": symbol, "date": event.date.isoformat(), "text": event.text.strip()}

    @app.delete("/events/{event_id}", status_code=204)
    def delete_event(event_id: int, c: sqlite3.Connection = Depends(conn)) -> Response:
        if not db.delete_event(c, event_id):
            raise HTTPException(404, "ไม่พบ event")
        return Response(status_code=204)

    return app


app = create_app(os.environ.get("SHORTLIST_DB", db.DEFAULT_PATH))
