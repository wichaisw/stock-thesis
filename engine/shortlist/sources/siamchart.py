from datetime import date, timedelta

from playwright.sync_api import sync_playwright

from shortlist.sources import NetFlow

PAGE_URL = "https://siamchart.com/stock-summary/"
# each net is rounded to 0.01 million; real days are up to 0.06 million off zero
MAX_NET_SUM = 0.1


def to_net_flows(market_data: list[list[str]], since: date) -> list[NetFlow]:
    """Rows of `market_data` ([date, local institution net, foreign net, individual net, SET], million baht) on or
    after `since`, in baht. Raises ValueError naming the first day whose nets do not sum to zero."""
    out = []
    for row in market_data:
        day = date.fromisoformat(row[0])
        if day < since:
            continue
        local, foreign, individual = (float(v) for v in row[1:4])
        if abs(local + foreign + individual) > MAX_NET_SUM:
            raise ValueError(f"ค่าสุทธิของวันที่ {day} รวมกันได้ {local + foreign + individual:,.2f} ล้านบาท ไม่ใช่ศูนย์")
        # 0.01 million is 10,000 baht, so whole baht loses nothing and drops float noise
        out.append(NetFlow(day, round(local * 1e6), round(foreign * 1e6), round(individual * 1e6)))
    return out


class SiamchartNetFlow:
    """siamchart.com sits behind Cloudflare, so the page's `market_data` is read from a headless browser."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_ms = timeout_seconds * 1000

    def fetch_net_flows(self, days: int = 366) -> list[NetFlow]:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.set_default_timeout(self.timeout_ms)
                page.goto(PAGE_URL)
                page.wait_for_function("typeof market_data !== 'undefined'")
                raw = page.evaluate("market_data")
            finally:
                browser.close()
        return to_net_flows(raw, date.today() - timedelta(days=days))
