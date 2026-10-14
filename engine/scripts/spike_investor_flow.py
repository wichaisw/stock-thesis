"""Spike (investor-type-flow design D1): does headless Chromium get past Incapsula on set.or.th?

Opens the SET investor-type page headless, then calls the JSON API from inside the page.
If Incapsula blocks it, stop here: do not try to evade the check.

    uv run python scripts/spike_investor_flow.py
"""

import json
import time

from playwright.sync_api import sync_playwright

PAGE = "https://www.set.or.th/th/market/statistics/investor-type"
API = "/api/set/market/SET/investor-type"


def main() -> None:
    start = time.monotonic()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            resp = page.goto(PAGE, timeout=30_000)
            print("page status:", resp.status if resp else None)
            result = page.evaluate(
                """async (url) => {
                    const r = await fetch(url);
                    return {status: r.status, body: await r.text()};
                }""",
                API,
            )
        finally:
            browser.close()
    print("api status:", result["status"])
    print(f"elapsed: {time.monotonic() - start:.1f}s")
    try:
        print(json.dumps(json.loads(result["body"]), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(result["body"][:500])


if __name__ == "__main__":
    main()
