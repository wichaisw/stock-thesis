"""Daily SET investor-type history from InfoQuest's "สรุปปริมาณการซื้อขายรายกลุ่ม ...(SET)" news (investor-type-flow
backfill, design D1 of daily-flow-backfill-chart). The article's og:description holds the date and the table."""

import html
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date

from shortlist.sources import INVESTOR_TYPES, InvestorFlow, check_investor_flow

LIST_URL = "https://www.infoquest.co.th/tag/investor_type/page/{page}"
USER_AGENT = "Mozilla/5.0 (shortlist; personal use)"
LABELS = {
    "institution": "สถาบันในประเทศ",
    "proprietary": "บัญชีบริษัทหลักทรัพย์",
    "foreign": "นักลงทุนต่างประเทศ",
    "individual": "นักลงทุนในประเทศ",
}
THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]
NUM = r"(-?[\d,]+\.\d+)"
# each value is rounded to 0.01 million, so buy − sell can be off the printed net by up to 0.01
MAX_NET_GAP = 0.015

Get = Callable[[str], str | None]


def set_article_links(page_html: str) -> list[str]:
    """Links of the SET-only articles on a listing page, in page order. The (SET+MAI) twins are skipped."""
    out: list[str] = []
    for url, text in re.findall(r'<a[^>]+href="(https://www\.infoquest\.co\.th/\d{4}/\d+)"[^>]*>(.*?)</a>', page_html, re.S):
        title = html.unescape(re.sub(r"<[^>]+>|\s+", " ", text)).strip()
        if title.startswith("สรุปปริมาณการซื้อขายรายกลุ่ม") and title.endswith("(SET)") and url not in out:
            out.append(url)
    return out


def article_to_flow(article_html: str) -> InvestorFlow:
    """Raises ValueError when the date or a type is missing, a net does not equal buy − sell, or the sums are off."""
    m = re.search(r'<meta property="og:description" content="([^"]*)"', article_html)
    if not m:
        raise ValueError("ไม่มี og:description")
    text = re.sub(r"\s+", " ", html.unescape(m.group(1)))
    d = re.search(r"ประจำวันที่ (\d{1,2}) (\S+) (\d{4})", text)
    if not d or d.group(2) not in THAI_MONTHS:
        raise ValueError("ไม่พบวันที่ของข้อมูล")
    day = date(int(d.group(3)) - 543, THAI_MONTHS.index(d.group(2)) + 1, int(d.group(1)))
    buy, sell, missing = {}, {}, []
    for t in INVESTOR_TYPES:
        row = re.search(rf"(?<!\S){LABELS[t]} {NUM} [\d.]+ {NUM} [\d.]+ {NUM}", text)
        if not row:
            missing.append(t)
            continue
        b, s, net = (float(v.replace(",", "")) for v in row.groups())
        if abs(b - s - net) > MAX_NET_GAP:
            raise ValueError(f"{day}: {t} ซื้อ − ขาย = {b - s:,.2f} ไม่เท่ากับสุทธิ {net:,.2f}")
        buy[t], sell[t] = round(b * 1e6), round(s * 1e6)
    if missing:
        raise ValueError(f"{day}: ขาดประเภทนักลงทุน: {', '.join(missing)}")
    # the article has no total; SET's total value equals the buy side
    try:
        return check_investor_flow(InvestorFlow(day, sum(buy.values()), buy, sell))
    except ValueError as e:
        raise ValueError(f"{day}: {e}") from e


def _http_get(url: str, timeout: float = 30.0) -> str | None:
    """Page text, or None on 404 (past the last listing page)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


class InfoQuestFlowHistory:
    def __init__(self, get: Get = _http_get, pause_seconds: float = 1.0):
        self.get = get
        self.pause = pause_seconds

    def _fetch(self, url: str) -> str | None:
        time.sleep(self.pause)  # one reader, politely spaced
        return self.get(url)

    def fetch_history(self) -> list[InvestorFlow]:
        """Every SET-only day the listing still has, oldest first. Raises on any HTTP error or bad article."""
        links: list[str] = []
        page = 1
        while (listing := self._fetch(LIST_URL.format(page=page))) is not None:
            links += [u for u in set_article_links(listing) if u not in links]
            page += 1
        flows: dict[date, InvestorFlow] = {}
        for url in links:
            body = self._fetch(url)
            if body is None:
                raise ValueError(f"ไม่พบข่าว {url}")
            try:
                flow = article_to_flow(body)
            except ValueError as e:
                raise ValueError(f"{url}: {e}") from e
            flows.setdefault(flow.date, flow)  # listing is newest first; a repost of a day keeps the newer one
        return sorted(flows.values(), key=lambda f: f.date)
