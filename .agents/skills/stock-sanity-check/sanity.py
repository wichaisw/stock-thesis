"""Flag outliers in the latest successful run; exits 1 when anything is flagged."""

import argparse
import json
import sys

import pandas as pd

from shortlist import db
from shortlist.config import load_config

MIN_MOS = -1.0
MAX_FV_TO_PRICE = 5.0
# fields the gate and bands read; dividend_yield is legitimately 0 or missing for non-payers
CHECKED_FIELDS = ["eps", "net_profit", "equity", "bvps", "close", "mkt_cap"]
# eps, bvps and close repeat legitimately after rounding; big baht figures almost never do
STALE_FIELDS = ["net_profit", "equity", "mkt_cap"]


def evaluation_flags(e: dict) -> list[str]:
    fv = e.get("fair_value") or {}
    out = []
    for item in fv.get("items", []):
        if item["fair_value"] is None:
            continue
        if item["mos"] is not None and item["mos"] < MIN_MOS:
            out.append(f"{item['method']} MoS {item['mos']:.0%}")
        if item["fair_value"] > MAX_FV_TO_PRICE * fv["price"]:
            out.append(f"{item['method']} fair value {item['fair_value']:,.2f} vs price {fv['price']:.2f}")
    return out


def quarterly_flags(q: pd.DataFrame, lookback: int, threshold: float, warned: bool) -> list[str]:
    # same window as core/fair_value: reported quarters only, so pre-IPO rows don't count
    hist = q[q["eps"].notna()].tail(lookback)
    out = []
    recent = hist.tail(4)
    for col in [c for c in CHECKED_FIELDS if c in q]:
        missing = recent.index[recent[col].isna()].tolist()
        if missing:
            out.append(f"{col} missing in {', '.join(missing)}")
    for col in [c for c in STALE_FIELDS if c in q]:
        s = hist[col]
        stale = hist.index[(s == s.shift()) & s.notna() & (s != 0)].tolist()
        if stale:
            out.append(f"{col} repeats previous quarter in {', '.join(stale)}")
    jump = hist["equity"].pct_change().abs()
    if not warned and jump.max() > threshold:
        out.append(f"equity changed {jump.max():.0%} in {jump.idxmax()} but no structure-change warning")
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--candidates-only", action="store_true")
    args = p.parse_args()

    cfg = load_config().fair_value
    conn = db.connect()
    run = db.latest_successful_run(conn)
    if run is None:
        sys.exit("no successful run; run `uv run shortlist-batch` first")
    sql = "SELECT symbol, result FROM evaluations WHERE run_id=?"
    if args.candidates_only:
        sql += " AND candidate_rank IS NOT NULL"
    quarterly = pd.read_sql("SELECT * FROM financials_quarterly", conn).set_index("quarter")

    flagged = 0
    for row in conn.execute(sql, (run["id"],)):
        e = json.loads(row["result"])
        flags = evaluation_flags(e)
        q = quarterly[quarterly.symbol == row["symbol"]]
        if not q.empty:
            warned = ((e.get("fair_value") or {}).get("structure_change") or {}).get("flag", False)
            flags += quarterly_flags(q, cfg.lookback_quarters, cfg.structure_change_threshold, warned)
        if flags:
            flagged += 1
            rank = f" (candidate #{e['candidate_rank']})" if e.get("candidate_rank") else ""
            print(f"{row['symbol']}{rank}\n  " + "\n  ".join(flags))
    print(f"\nrun {run['id']} ({run['price_date']}): {flagged} symbols flagged")
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
