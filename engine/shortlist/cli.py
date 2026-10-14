import argparse
import sys
import time
from datetime import datetime
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
        prices, financials, flow = batch.default_sources(cfg)
        run_id = batch.run(
            conn, prices, financials, cfg, log=lambda m: print(f"{datetime.now():%H:%M:%S} {m}", flush=True), flow_src=flow
        )
    except db.RunInProgress as e:
        sys.exit(str(e))
    except batch.BatchAborted:
        sys.exit(1)  # the reason is already in the log and saved on the run
    run = db.get_run(conn, run_id)
    assert run is not None
    print(
        f"run {run_id} {run['status']} ใน {time.monotonic() - started:.0f} วินาที: "
        f"สำเร็จ {run['succeeded']}/{run['total']} fail {run['failed']} ราคาวันที่ {run['price_date']}"
    )


def backfill_flow() -> None:
    """One-off: a year of daily net values by investor group from siamchart (design D5)."""
    from shortlist.sources.siamchart import SiamchartNetFlow

    parser = argparse.ArgumentParser(description="เติมค่าสุทธิตามประเภทนักลงทุนย้อนหลัง 1 ปีจาก siamchart")
    parser.add_argument("--db", type=Path, default=db.DEFAULT_PATH)
    args = parser.parse_args()
    try:
        flows = SiamchartNetFlow().fetch_net_flows()
    except Exception as e:
        sys.exit(f"เติมย้อนหลังไม่ได้: {type(e).__name__}: {e}")
    db.save_net_flows(db.connect(args.db), flows)
    if flows:
        print(f"เก็บค่าสุทธิ {len(flows)} วัน ตั้งแต่ {flows[0].date} ถึง {flows[-1].date}")
    else:
        print("siamchart ไม่มีข้อมูลในช่วง 1 ปี")


if __name__ == "__main__":
    main()
