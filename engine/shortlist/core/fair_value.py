from statistics import median

import pandas as pd

from shortlist.config import FairValue
from shortlist.core import num

LABELS = {
    "pe_median": "PE band (median 5 ปี)",
    "pe_minus_1sd": "PE band (median − 1SD)",
    "pbv_median": "PBV band (median 5 ปี)",
    "dividend_yield_median": "Dividend yield band (median 5 ปี)",
    "peer_pe": "Peer PE (median ของ sector)",
}


def eps_ttm(quarterly: pd.DataFrame) -> float | None:
    eps = quarterly["eps"].dropna()
    return float(eps.tail(4).sum()) if len(eps) >= 4 else None


def current_pe(quarterly: pd.DataFrame, price: float) -> float | None:
    """PE on today's price; None when EPS TTM is not positive (PE is meaningless then)."""
    ttm = eps_ttm(quarterly)
    return price / ttm if ttm and ttm > 0 else None


def peers_for(symbol: str, sector: str, pe_by_symbol: dict[str, tuple[str, float | None]]) -> list[float]:
    return [pe for s, (sec, pe) in pe_by_symbol.items() if sec == sector and s != symbol and pe is not None]


def evaluate(quarterly: pd.DataFrame, price: float, peer_pes: list[float], cfg: FairValue) -> dict:
    reported = quarterly[quarterly["eps"].notna()]
    hist = reported.tail(cfg.lookback_quarters)
    ttm = eps_ttm(reported)
    pe_hist = (reported["close"] / reported["eps"].rolling(4).sum()).tail(cfg.lookback_quarters)
    # a near-zero EPS TTM gives a PE in the hundreds, which would blow up the SD
    pe_hist = pe_hist[(pe_hist > 0) & (pe_hist <= cfg.max_pe)]

    def fair(method: str) -> tuple[float | None, str | None]:
        if method in ("pe_median", "pe_minus_1sd", "peer_pe"):
            if ttm is None:
                return None, "งบไม่ครบ 4 ไตรมาสสำหรับ EPS TTM"
            if ttm <= 0:
                return None, "EPS TTM ติดลบ"
        if method in ("pe_median", "pe_minus_1sd"):
            if len(pe_hist) < cfg.min_history_points:
                return None, "ข้อมูล PE ย้อนหลังไม่พอ"
            multiple = pe_hist.median() - (pe_hist.std() if method == "pe_minus_1sd" else 0)
            if multiple <= 0:
                return None, "PE median − 1SD ไม่เป็นบวก"
            return multiple * ttm, None
        if method == "peer_pe":
            if len(peer_pes) < cfg.min_peers:
                return None, f"peer ใน sector มี {len(peer_pes)} ตัว น้อยกว่า {cfg.min_peers}"
            return median(peer_pes) * ttm, None
        if method == "pbv_median":
            with_bv = hist[hist["bvps"] > 0]
            pbv = with_bv["close"] / with_bv["bvps"]
            if len(pbv.dropna()) < cfg.min_history_points:
                return None, "ข้อมูล PBV ย้อนหลังไม่พอ"
            return pbv.median() * with_bv["bvps"].iloc[-1], None
        if method == "dividend_yield_median":
            paid = hist["dividend_yield"][hist["dividend_yield"] > 0]
            if paid.empty:
                return None, "ไม่มีปันผลในช่วง 5 ปี"
            # a couple of stray tiny yields would make the median ~0 and the fair value explode
            if len(paid) < cfg.min_history_points:
                return None, f"มีปันผลแค่ {len(paid)} ไตรมาสในช่วง 5 ปี"
            # thaifin often shows 0 in the quarters after the payout, so look back a full year
            recent = paid[paid.index.isin(hist.index[-4:])]
            if recent.empty:
                return None, "ไม่ได้จ่ายปันผลใน 4 ไตรมาสล่าสุด"
            # thaifin has no DPS; yield × that quarter's close recovers it
            dps = recent.iloc[-1] * hist.loc[recent.index[-1], "close"]
            return dps / paid.median(), None
        raise ValueError(method)

    items = []
    for method in cfg.enabled:
        value, reason = fair(method)
        value = num(value, 2)
        items.append(
            {
                "method": method,
                "label": LABELS[method],
                "fair_value": value,
                "mos": num((value - price) / value, 4) if value else None,
                "reason": reason,
            }
        )
    return {"price": price, "eps_ttm": num(ttm, 4), "items": items, "summary": summarize(items)}


def summarize(items: list[dict]) -> dict:
    done = [i for i in items if i["mos"] is not None]
    if not done:
        return {"label": "0/0 undervalued", "undervalued": 0, "computed": 0, "min_mos": None,
                "median_mos": None, "max_mos": None, "median_fair_value": None, "max_fair_value": None}
    mos = [i["mos"] for i in done]
    fvs = [i["fair_value"] for i in done]
    undervalued = sum(m > 0 for m in mos)
    return {
        "label": f"{undervalued}/{len(done)} undervalued",
        "undervalued": undervalued,
        "computed": len(done),
        "min_mos": min(mos),
        "median_mos": num(median(mos), 4),
        "max_mos": max(mos),
        "median_fair_value": num(median(fvs), 2),
        "max_fair_value": max(fvs),
    }
