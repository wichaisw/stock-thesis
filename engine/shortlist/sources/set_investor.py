from datetime import datetime

from playwright.sync_api import sync_playwright

from shortlist.sources import INVESTOR_TYPES, InvestorFlow, InvestorFlowFetch, MonthlyNetFlow

PAGE_URL = "https://www.set.or.th/th/market/statistics/investor-type"
API_PATH = "/api/set/market/SET/investor-type"
CHART_PATH = "/api/set/market/SET/investor-type-chart?period=1Y"
MAX_SUM_GAP = 0.01
# buys equal sells market-wide; real sets are off by a few baht of float noise
MAX_NET_SUM = 1e6


def to_investor_flow(raw: dict) -> InvestorFlow:
    """Raises ValueError when a type is missing or the buy or sell sum is more than 1% off the total."""
    by_type = {i["type"]: i for i in raw["investors"]}
    missing = [t for t in INVESTOR_TYPES if t not in by_type]
    if missing:
        raise ValueError(f"ขาดประเภทนักลงทุน: {', '.join(missing)}")
    total = float(raw["totalValue"])
    buy = {t: float(by_type[t]["buyValue"]) for t in INVESTOR_TYPES}
    sell = {t: float(by_type[t]["sellValue"]) for t in INVESTOR_TYPES}
    for side, values in (("ซื้อ", buy), ("ขาย", sell)):
        if abs(sum(values.values()) - total) > MAX_SUM_GAP * total:
            raise ValueError(f"ผลรวมมูลค่า{side} {sum(values.values()):,.0f} ต่างจากมูลค่ารวม {total:,.0f} เกิน 1%")
    return InvestorFlow(datetime.fromisoformat(raw["asOfDate"]).date(), total, buy, sell)


def to_monthly_net(raw: list[dict]) -> list[MonthlyNetFlow]:
    """Raises ValueError when there are no points, a month repeats, a type is missing or the 4 nets do not sum to zero."""
    if not raw:
        raise ValueError("กราฟรายเดือนไม่มีข้อมูล")
    out: list[MonthlyNetFlow] = []
    for point in raw:
        month = datetime.fromisoformat(point["date"]).strftime("%Y-%m")
        missing = [t for t in INVESTOR_TYPES if point.get(t) is None]
        if missing:
            raise ValueError(f"เดือน {month} ขาดประเภทนักลงทุน: {', '.join(missing)}")
        net = {t: float(point[t]) for t in INVESTOR_TYPES}
        if abs(sum(net.values())) > MAX_NET_SUM:
            raise ValueError(f"ค่าสุทธิของเดือน {month} รวมกันได้ {sum(net.values()) / 1e6:,.2f} ล้านบาท ไม่ใช่ศูนย์")
        if out and month <= out[-1].month:
            raise ValueError(f"เดือน {month} ซ้ำหรือไม่เรียงตามเวลา")
        out.append(MonthlyNetFlow(month, net))
    return out


def _parse(response: dict, convert):
    """(value, None) or (None, why), so one bad part does not drop the other."""
    if response["status"] != 200:
        return None, f"HTTP {response['status']}"
    try:
        return convert(response["body"]), None
    except ValueError as e:
        return None, str(e)
    except (KeyError, TypeError) as e:
        return None, f"รูปแบบข้อมูลเปลี่ยน: {type(e).__name__}: {e}"


class SetInvestorFlow:
    """SET blocks plain HTTP clients (Incapsula), so the API is called from inside a headless page."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_ms = timeout_seconds * 1000

    def fetch_investor_flow(self) -> InvestorFlowFetch:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.set_default_timeout(self.timeout_ms)
                page.goto(PAGE_URL)
                daily, chart = page.evaluate(
                    """async ([urls, ms]) => Promise.all(urls.map(async (url) => {
                        const r = await fetch(url, {signal: AbortSignal.timeout(ms)});
                        return {status: r.status, body: r.ok ? await r.json() : null};
                    }))""",
                    [[API_PATH, CHART_PATH], self.timeout_ms],
                )
            finally:
                browser.close()
        flow, flow_error = _parse(daily, to_investor_flow)
        monthly, monthly_error = _parse(chart, to_monthly_net)
        return InvestorFlowFetch(flow, monthly, flow_error, monthly_error)
