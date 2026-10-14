import argparse
import sys
import time
from pathlib import Path

from shortlist import batch, db
from shortlist.config import DEFAULT_PATH as CONFIG_PATH
from shortlist.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="รัน batch ดึงข้อมูลและประเมินหุ้นทั้งตลาด")
    parser.add_argument("--db", type=Path, default=db.DEFAULT_PATH)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()

    conn = db.connect(args.db)
    # same values as the web button: config.yaml plus what was edited on the settings page
    cfg = load_config(args.config, db.settings(conn))
    started = time.monotonic()
    try:
        run_id = batch.run(conn, *batch.default_sources(cfg), cfg, log=lambda m: print(m, flush=True))
    except db.RunInProgress as e:
        sys.exit(str(e))
    run = db.get_run(conn, run_id)
    assert run is not None
    print(
        f"run {run_id} {run['status']} ใน {time.monotonic() - started:.0f} วินาที: "
        f"สำเร็จ {run['succeeded']}/{run['total']} fail {run['failed']} ราคาวันที่ {run['price_date']}"
    )


if __name__ == "__main__":
    main()
