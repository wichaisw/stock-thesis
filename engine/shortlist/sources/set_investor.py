from datetime import datetime

from playwright.sync_api import sync_playwright

from shortlist.sources import INVESTOR_TYPES, InvestorFlow

PAGE_URL = "https://www.set.or.th/th/market/statistics/investor-type"
API_PATH = "/api/set/market/SET/investor-type"
MAX_SUM_GAP = 0.01


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


class SetInvestorFlow:
    """SET blocks plain HTTP clients (Incapsula), so the API is called from inside a headless page."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_ms = timeout_seconds * 1000

    def fetch_investor_flow(self) -> InvestorFlow:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.set_default_timeout(self.timeout_ms)
                page.goto(PAGE_URL)
                raw = page.evaluate(
                    """async ([url, ms]) => {
                        const r = await fetch(url, {signal: AbortSignal.timeout(ms)});
                        if (!r.ok) throw new Error(`HTTP ${r.status}`);
                        return r.json();
                    }""",
                    [API_PATH, self.timeout_ms],
                )
            finally:
                browser.close()
        return to_investor_flow(raw)
