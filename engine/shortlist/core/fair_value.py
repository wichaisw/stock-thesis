from statistics import median

import pandas as pd

from shortlist.config import FairValue
from shortlist.core import num
from shortlist.core.quality import roe_ttm

LABELS = {
    "pe_median": "PE band (median 5 ปี)",
    "pe_minus_1sd": "PE band (median − 1SD)",
    "pbv_median": "PBV band (median 5 ปี)",
    "dividend_yield_median": "Dividend yield band (median 5 ปี)",
    "peer_pe": "Peer PE (median ของ sector)",
    "justified_pbv": "Justified PBV ((ROE − g) ÷ (r − g))",
}

# both PE lines read the same profit TTM, so together they are one independent view in the summary
VIEW = {"pe_minus_1sd": "pe_median"}


def eps_ttm(quarterly: pd.DataFrame) -> float | None:
    eps = quarterly["eps"].dropna()
    return float(eps.tail(4).sum()) if len(eps) >= 4 else None


def net_profit_ttm(quarterly: pd.DataFrame) -> float | None:
    profit = quarterly["net_profit"].dropna()
    return float(profit.tail(4).sum()) if len(profit) >= 4 else None


def latest_shares(caps: pd.DataFrame) -> float | None:
    shares = caps["shares"].dropna()
    return float(shares.iloc[-1]) if len(shares) else None


def current_pe(quarterly: pd.DataFrame, price: float, caps: pd.DataFrame) -> float | None:
    """Company-level PE on today's price; None when profit TTM is not positive (PE is meaningless then)."""
    ttm, shares = net_profit_ttm(quarterly), latest_shares(caps)
    return price * shares / ttm if ttm and ttm > 0 and shares else None


def peers_for(symbol: str, sector: str, pe_by_symbol: dict[str, tuple[str, float | None]]) -> list[float]:
    return [pe for s, (sec, pe) in pe_by_symbol.items() if sec == sector and s != symbol and pe is not None]


def evaluate(quarterly: pd.DataFrame, price: float, peer_pes: list[float], cfg: FairValue, caps: pd.DataFrame) -> dict:
    """PE/PBV bands are company-level (market cap ÷ profit or equity) and converted back with today's
    share count, so splits, capital raises and the source's dividend-adjusted prices don't skew them."""
    reported = quarterly[quarterly["eps"].notna()].join(caps[["mkt_cap"]])
    hist = reported.tail(cfg.lookback_quarters)
    ttm = net_profit_ttm(reported)
    shares = latest_shares(caps)
    has_cap = hist["mkt_cap"].notna()
    pe_hist = (reported["mkt_cap"] / reported["net_profit"].rolling(4).sum()).tail(cfg.lookback_quarters)
    # a near-zero profit TTM gives a PE in the hundreds, which would blow up the SD
    pe_hist = pe_hist[(pe_hist > 0) & (pe_hist <= cfg.max_pe)]

    def fair(method: str) -> tuple[float | None, str | None]:
        if method in ("pe_median", "pe_minus_1sd", "pbv_median") and not has_cap.any():
            return None, "ไม่มี market cap ย้อนหลัง"
        if method in ("pe_median", "pe_minus_1sd", "peer_pe", "pbv_median", "justified_pbv") and not shares:
            return None, "ไม่มีจำนวนหุ้นล่าสุด"
        if method in ("pe_median", "pe_minus_1sd", "peer_pe"):
            if ttm is None:
                return None, "งบไม่ครบ 4 ไตรมาสสำหรับกำไร TTM"
            if ttm <= 0:
                return None, "กำไร 4 ไตรมาสติดลบ"
        if method in ("pe_median", "pe_minus_1sd"):
            if len(pe_hist) < cfg.min_history_points:
                return None, "ข้อมูล PE ย้อนหลังไม่พอ"
            multiple = pe_hist.median() - (pe_hist.std() if method == "pe_minus_1sd" else 0)
            if multiple <= 0:
                return None, "PE median − 1SD ไม่เป็นบวก"
            return multiple * ttm / shares, None
        if method == "peer_pe":
            if len(peer_pes) < cfg.min_peers:
                return None, f"peer ใน sector มี {len(peer_pes)} ตัว น้อยกว่า {cfg.min_peers}"
            return median(peer_pes) * ttm / shares, None
        if method == "pbv_median":
            with_equity = hist[hist["equity"] > 0]
            pbv = (with_equity["mkt_cap"] / with_equity["equity"]).dropna()
            if len(pbv) < cfg.min_history_points:
                return None, "ข้อมูล PBV ย้อนหลังไม่พอ"
            return pbv.median() * with_equity["equity"].iloc[-1] / shares, None
        if method == "dividend_yield_median":
            # cash yields from the price source, not the statement source: stock dividends and the
            # source's odd off-quarter values would drag the median toward 0 and inflate fair value
            # windowed on the price source's quarters, so funds without statements in the source still get a band
            floor = cfg.min_dividend_yield
            yields = caps["dividend_yield_ttm"].dropna().tail(cfg.lookback_quarters)
            paid = yields[yields >= floor]
            if paid.empty:
                return None, f"ไม่มีไตรมาสที่จ่ายปันผลเงินสดถึงเกณฑ์ {floor:.1%}"
            latest = caps[["dps_ttm", "dividend_yield_ttm"]].dropna()
            if latest.empty or latest["dividend_yield_ttm"].iloc[-1] < floor:
                return None, "ไม่ได้จ่ายปันผลเงินสดใน 12 เดือนล่าสุด"
            if len(paid) < cfg.min_history_points:
                return None, f"จ่ายปันผลเงินสดถึงเกณฑ์แค่ {len(paid)} ไตรมาสในช่วง 5 ปี"
            return latest["dps_ttm"].iloc[-1] / paid.median(), None
        if method == "justified_pbv":
            # same ROE TTM as the quality gate, so the detail page shows one ROE
            roe, r, g = roe_ttm(reported), cfg.cost_of_equity, cfg.terminal_growth
            if roe is None:
                return None, "คำนวณ ROE TTM ไม่ได้"
            if roe <= g:
                return None, f"ROE TTM {roe:.1%} ไม่สูงกว่า g {g:.1%}"
            return (roe - g) / (r - g) * reported["equity"].dropna().iloc[-1] / shares, None
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
    return {
        "price": price,
        "eps_ttm": num(eps_ttm(reported), 4),
        "items": items,
        "summary": summarize(items),
        "structure_change": structure_change(hist, cfg.structure_change_threshold),
        "history_gap": history_gap(has_cap),
    }


def history_gap(has_cap: pd.Series) -> dict:
    """Quarters without a market cap (no share count before a rename or merger) are skipped in the bands."""
    if has_cap.all():
        return {"flag": False, "reason": None}
    return {
        "flag": True,
        "reason": f"มี market cap ย้อนหลัง {int(has_cap.sum())}/{len(has_cap)} ไตรมาส band คิดจากเท่าที่มี",
    }


def structure_change(hist: pd.DataFrame, threshold: float) -> dict:
    """Mergers, capital raises and restructurings make the band history incomparable.

    Equity, not share count: a par split changes the share count but leaves PE/PBV history intact.
    """
    change = hist["equity"].pct_change().abs()
    if change.dropna().empty or change.max() <= threshold:
        return {"flag": False, "reason": None}
    quarter = change.idxmax()
    return {
        "flag": True,
        "reason": f"ส่วนผู้ถือหุ้นเปลี่ยน {change.max():.0%} ใน {quarter} band ย้อนหลังอาจเทียบกับปัจจุบันไม่ได้",
    }


def summarize(items: list[dict]) -> dict:
    done = [i for i in items if i["mos"] is not None]
    if not done:
        return {"label": "0/0 undervalued", "undervalued": 0, "computed": 0, "min_mos": None,
                "median_mos": None, "max_mos": None, "median_fair_value": None, "max_fair_value": None}
    mos = [i["mos"] for i in done]
    fvs = [i["fair_value"] for i in done]
    views: dict[str, list[float]] = {}
    for i in done:
        views.setdefault(VIEW.get(i["method"], i["method"]), []).append(i["mos"])
    undervalued = sum(sum(v) / len(v) > 0 for v in views.values())
    return {
        "label": f"{undervalued}/{len(views)} undervalued",
        "undervalued": undervalued,
        "computed": len(views),
        "min_mos": min(mos),
        "median_mos": num(median(mos), 4),
        "max_mos": max(mos),
        "median_fair_value": num(median(fvs), 2),
        "max_fair_value": max(fvs),
    }
