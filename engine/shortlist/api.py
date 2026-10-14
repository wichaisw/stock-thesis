import logging
import sqlite3
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from shortlist import batch, db
from shortlist.config import DEFAULT_PATH as CONFIG_PATH
from shortlist.config import Config, load_config
from shortlist.core import catalyst

log = logging.getLogger("shortlist")


class EventIn(BaseModel):
    date: date
    text: str = Field(min_length=1, max_length=200)


def create_app(
    db_path: Path | str = db.DEFAULT_PATH,
    config_path: Path = CONFIG_PATH,
    sources: Callable[[Config], tuple] = batch.default_sources,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    app = FastAPI(title="shortlist engine")

    def conn() -> Iterator[sqlite3.Connection]:
        c = db.connect(db_path)
        try:
            yield c
        finally:
            c.close()

    def run_in_background(run_id: int) -> None:
        c = db.connect(db_path)
        try:
            try:
                cfg = load_config(config_path)
                prices, financials = sources(cfg)
            except Exception as e:
                db.fail_run(c, run_id, f"{type(e).__name__}: {e}")
                raise
            batch.execute(c, run_id, prices, financials, cfg, today())
        except Exception:
            # the run is already marked failed; keep the server alive
            log.exception("batch run %s failed", run_id)
        finally:
            c.close()

    @app.get("/runs/latest")
    def latest_runs(c: sqlite3.Connection = Depends(conn)) -> dict:
        return {"latest": db.latest_run(c), "latest_succeeded": db.latest_successful_run(c)}

    @app.post("/runs", status_code=202)
    def start_run(tasks: BackgroundTasks, c: sqlite3.Connection = Depends(conn)) -> dict:
        cfg = load_config(config_path)
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
        if not run:
            return {"run": None, "candidates": [], "failure_count": 0}
        return {"run": run, "candidates": db.candidates(c, run["id"]), "failure_count": run["failed"]}

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
        cfg = load_config(config_path)
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


app = create_app()
